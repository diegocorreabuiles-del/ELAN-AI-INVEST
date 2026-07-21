from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile, ZipInfo

SCHEMA_VERSION = 1
PROJECT_NAME = "elan-ai-invest"
MANIFEST_NAME = "DISTRIBUTION_MANIFEST.json"
EMPTY_DIRECTORIES = ("data/", "logs/")
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_FILE_COUNT = 5_000
REQUIRED_FILES = {
    "app.py",
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    "requirements.lock",
    "run.bat",
    "install.bat",
    "update.bat",
    "config/settings.yaml",
    "scripts/build_distribution.py",
    "src/elan_ai_invest/__init__.py",
}
BLOCKED_SEGMENTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "build",
    "data",
    "dist",
    "htmlcov",
    "logs",
    "otros",
}
BLOCKED_SUFFIXES = {
    ".db",
    ".exe",
    ".key",
    ".log",
    ".p12",
    ".pem",
    ".pfx",
    ".pickle",
    ".pkl",
    ".pyc",
    ".sqlite",
    ".sqlite3",
    ".zip",
}
SENSITIVE_NAMES = {
    ".npmrc",
    ".pypirc",
    "api_key",
    "apikey",
    "credential",
    "credentials",
    "id_ed25519",
    "id_rsa",
    "passwd",
    "password",
    "private_key",
    "secret",
    "secrets",
    "token",
}
WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


class DistributionError(ValueError):
    """Raised when an archive cannot be built or verified safely."""


@dataclass(frozen=True)
class TreeEntry:
    mode: str
    object_id: str
    path: str


@dataclass(frozen=True)
class BuildResult:
    output: Path
    root: str
    commit: str
    file_count: int
    sha256: str


def _git_executable(configured: str | None = None) -> str:
    executable = configured or os.environ.get("GIT_EXECUTABLE") or shutil.which("git")
    if not executable:
        raise DistributionError("No se encontró Git; defina GIT_EXECUTABLE con su ruta.")
    return executable


def _git(
    root: Path,
    *arguments: str,
    git_executable: str | None = None,
) -> bytes:
    process = subprocess.run(
        [_git_executable(git_executable), *arguments],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if process.returncode != 0:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise DistributionError(
            f"Git falló ({' '.join(arguments)}): {detail or 'error desconocido'}"
        )
    return process.stdout


def _safe_relative_path(raw_path: str) -> PurePosixPath:
    if not raw_path or "\\" in raw_path or raw_path.startswith(("/", "//")):
        raise DistributionError(f"Ruta insegura o no portable: {raw_path!r}.")
    if any(ord(character) < 32 for character in raw_path):
        raise DistributionError(f"Ruta insegura con caracteres de control: {raw_path!r}.")

    path = PurePosixPath(raw_path)
    if path.as_posix() != raw_path or any(part in {"", ".", ".."} for part in path.parts):
        raise DistributionError(f"Ruta insegura o no normalizada: {raw_path!r}.")

    for part in path.parts:
        if part.endswith((" ", ".")) or any(character in '<>:"|?*' for character in part):
            raise DistributionError(f"Ruta no portable en Windows: {raw_path!r}.")
        if part.split(".", 1)[0].upper() in WINDOWS_RESERVED:
            raise DistributionError(f"Nombre reservado de Windows: {raw_path!r}.")
    return path


def _validate_source_path(raw_path: str) -> PurePosixPath:
    path = _safe_relative_path(raw_path)
    lowered_parts = tuple(part.casefold() for part in path.parts)
    if any(part in BLOCKED_SEGMENTS for part in lowered_parts):
        raise DistributionError(f"Ruta bloqueada para distribución: {raw_path!r}.")

    filename = path.name.casefold()
    if filename == ".env" or filename.startswith(".env."):
        raise DistributionError(f"Archivo de entorno bloqueado: {raw_path!r}.")
    if path.suffix.casefold() in BLOCKED_SUFFIXES:
        raise DistributionError(f"Extensión bloqueada para distribución: {raw_path!r}.")

    normalized_name = re.sub(r"[^a-z0-9]+", "_", filename).strip("_")
    name_tokens = set(normalized_name.split("_"))
    sensitive_tokens = {
        "credential",
        "credentials",
        "passwd",
        "password",
        "secret",
        "secrets",
        "token",
    }
    if (
        filename in SENSITIVE_NAMES
        or normalized_name in SENSITIVE_NAMES
        or name_tokens & sensitive_tokens
    ):
        raise DistributionError(f"Nombre sensible bloqueado: {raw_path!r}.")
    if {"api", "key"}.issubset(name_tokens) or {"private", "key"}.issubset(name_tokens):
        raise DistributionError(f"Nombre sensible bloqueado: {raw_path!r}.")
    return path


def _repository_root(root: Path, git_executable: str | None) -> Path:
    requested = root.resolve()
    discovered = Path(
        _git(requested, "rev-parse", "--show-toplevel", git_executable=git_executable)
        .decode("utf-8")
        .strip()
    ).resolve()
    if discovered != requested:
        raise DistributionError(
            f"Use la raíz exacta del repositorio: {discovered}; se recibió {requested}."
        )
    return discovered


def _assert_clean(root: Path, git_executable: str | None) -> None:
    status_output = _git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        git_executable=git_executable,
    )
    if status_output.strip():
        raise DistributionError(
            "El working tree debe estar limpio; confirme los cambios antes de construir el ZIP."
        )


def _tree_entries(root: Path, git_executable: str | None) -> list[TreeEntry]:
    output = _git(
        root,
        "ls-tree",
        "-r",
        "-z",
        "--full-tree",
        "HEAD",
        git_executable=git_executable,
    )
    entries: list[TreeEntry] = []
    seen_casefolded: set[str] = set()
    for record in output.split(b"\0"):
        if not record:
            continue
        try:
            metadata, encoded_path = record.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split()
            path = encoded_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise DistributionError("Git contiene una entrada que no es UTF-8 portable.") from exc
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise DistributionError(f"Tipo de entrada Git no permitido: {mode} {path!r}.")
        _validate_source_path(path)
        folded = path.casefold()
        if folded in seen_casefolded:
            raise DistributionError(f"Colisión de ruta sin distinguir mayúsculas: {path!r}.")
        seen_casefolded.add(folded)
        entries.append(TreeEntry(mode=mode, object_id=object_id, path=path))

    actual_paths = {entry.path for entry in entries}
    missing = sorted(REQUIRED_FILES - actual_paths)
    if missing:
        raise DistributionError(f"Faltan archivos operativos en HEAD: {', '.join(missing)}.")
    if len(entries) > MAX_FILE_COUNT:
        raise DistributionError(f"HEAD supera el límite de {MAX_FILE_COUNT} archivos.")
    return sorted(entries, key=lambda item: item.path)


def _blob(root: Path, entry: TreeEntry, git_executable: str | None) -> bytes:
    content = _git(root, "cat-file", "blob", entry.object_id, git_executable=git_executable)
    if len(content) > MAX_FILE_BYTES:
        raise DistributionError(
            f"{entry.path!r} supera el límite de {MAX_FILE_BYTES // (1024 * 1024)} MiB."
        )
    return content


def _project_version(pyproject_content: bytes) -> str:
    try:
        data = tomllib.loads(pyproject_content.decode("utf-8"))
        version = data["project"]["version"]
    except (KeyError, TypeError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise DistributionError("No se pudo obtener project.version de pyproject.toml.") from exc
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]*", version):
        raise DistributionError(f"Versión no portable en pyproject.toml: {version!r}.")
    return version


def _zip_timestamp(commit_timestamp: int) -> tuple[int, int, int, int, int, int]:
    moment = datetime.fromtimestamp(commit_timestamp, UTC)
    year = min(max(moment.year, 1980), 2107)
    return (year, moment.month, moment.day, moment.hour, moment.minute, moment.second // 2 * 2)


def _zip_info(name: str, timestamp: tuple[int, int, int, int, int, int], mode: int) -> ZipInfo:
    info = ZipInfo(name, date_time=timestamp)
    info.compress_type = ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = mode << 16
    info.flag_bits |= 0x800
    return info


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _archive_bytes(
    root: Path,
    entries: list[TreeEntry],
    commit: str,
    commit_timestamp: int,
    git_executable: str | None,
    destination: Path,
) -> tuple[str, int]:
    contents = {entry.path: _blob(root, entry, git_executable) for entry in entries}
    version = _project_version(contents["pyproject.toml"])
    archive_root = f"elan-quantum-{version}"
    timestamp = _zip_timestamp(commit_timestamp)
    files = [
        {
            "path": entry.path,
            "size": len(contents[entry.path]),
            "sha256": _sha256(contents[entry.path]),
        }
        for entry in entries
    ]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "project": PROJECT_NAME,
        "version": version,
        "commit": commit,
        "root": archive_root,
        "files": files,
        "empty_directories": list(EMPTY_DIRECTORIES),
    }
    manifest_content = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for entry in entries:
            permission = 0o100755 if entry.mode == "100755" else 0o100644
            archive.writestr(
                _zip_info(f"{archive_root}/{entry.path}", timestamp, permission),
                contents[entry.path],
                compresslevel=9,
            )
        archive.writestr(
            _zip_info(f"{archive_root}/{MANIFEST_NAME}", timestamp, 0o100644),
            manifest_content,
            compresslevel=9,
        )
        for directory in EMPTY_DIRECTORIES:
            archive.writestr(
                _zip_info(f"{archive_root}/{directory}", timestamp, 0o40755),
                b"",
                compresslevel=9,
            )
    return archive_root, len(entries)


def _validate_member_name(name: str) -> PurePosixPath:
    candidate = name[:-1] if name.endswith("/") else name
    if not candidate:
        raise DistributionError("El ZIP contiene una ruta insegura vacía.")
    try:
        return _safe_relative_path(candidate)
    except DistributionError as exc:
        raise DistributionError(f"El ZIP contiene una ruta insegura: {name!r}.") from exc


def _is_symlink(info: ZipInfo) -> bool:
    return info.create_system == 3 and stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK


def verify_archive(archive_path: Path) -> dict[str, Any]:
    path = archive_path.resolve()
    if not path.is_file():
        raise DistributionError(f"No existe el ZIP: {path}.")
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise DistributionError("El ZIP supera el tamaño máximo permitido.")

    try:
        with ZipFile(path) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > MAX_FILE_COUNT + 3:
                raise DistributionError("El ZIP está vacío o contiene demasiadas entradas.")

            names: set[str] = set()
            folded_names: set[str] = set()
            roots: set[str] = set()
            total_size = 0
            for info in infos:
                member_path = _validate_member_name(info.filename)
                roots.add(member_path.parts[0])
                if info.filename in names or info.filename.casefold() in folded_names:
                    raise DistributionError(f"Entrada duplicada en el ZIP: {info.filename!r}.")
                names.add(info.filename)
                folded_names.add(info.filename.casefold())
                if info.flag_bits & 0x1:
                    raise DistributionError(f"Entrada cifrada no permitida: {info.filename!r}.")
                if _is_symlink(info):
                    raise DistributionError(
                        f"El ZIP contiene un enlace simbólico: {info.filename!r}."
                    )
                if info.file_size > MAX_FILE_BYTES:
                    raise DistributionError(f"Entrada demasiado grande: {info.filename!r}.")
                total_size += info.file_size
            if total_size > MAX_ARCHIVE_BYTES or len(roots) != 1:
                raise DistributionError("El ZIP debe contener una única raíz portable y acotada.")

            archive_root = next(iter(roots))
            manifest_path = f"{archive_root}/{MANIFEST_NAME}"
            if manifest_path not in names:
                raise DistributionError(f"Falta {MANIFEST_NAME} en el ZIP.")
            try:
                manifest = json.loads(archive.read(manifest_path).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise DistributionError("El manifiesto no es JSON UTF-8 válido.") from exc

            required_keys = {
                "schema_version",
                "project",
                "version",
                "commit",
                "root",
                "files",
                "empty_directories",
            }
            if not isinstance(manifest, dict) or set(manifest) != required_keys:
                raise DistributionError("El manifiesto no cumple el esquema esperado.")
            if manifest["schema_version"] != SCHEMA_VERSION or manifest["project"] != PROJECT_NAME:
                raise DistributionError("El manifiesto usa un proyecto o esquema no compatible.")
            if manifest["root"] != archive_root:
                raise DistributionError("La raíz del manifiesto no coincide con la del ZIP.")
            if (
                not isinstance(manifest["version"], str)
                or archive_root != f"elan-quantum-{manifest['version']}"
            ):
                raise DistributionError("La versión no coincide con la raíz del ZIP.")
            if not isinstance(manifest["commit"], str) or not re.fullmatch(
                r"[0-9a-f]{40,64}", manifest["commit"]
            ):
                raise DistributionError("El commit del manifiesto no es válido.")
            if manifest["empty_directories"] != list(EMPTY_DIRECTORIES):
                raise DistributionError(
                    "Las carpetas de estado vacías no coinciden con el contrato."
                )
            if not isinstance(manifest["files"], list) or not manifest["files"]:
                raise DistributionError("El manifiesto no contiene archivos.")

            expected_names = {manifest_path}
            manifested_paths: set[str] = set()
            for item in manifest["files"]:
                if not isinstance(item, dict) or set(item) != {"path", "size", "sha256"}:
                    raise DistributionError("Una entrada del manifiesto no cumple el esquema.")
                relative = item["path"]
                if not isinstance(relative, str):
                    raise DistributionError("El manifiesto contiene una ruta no textual.")
                _validate_source_path(relative)
                if relative in manifested_paths:
                    raise DistributionError(f"Ruta duplicada en el manifiesto: {relative!r}.")
                manifested_paths.add(relative)
                full_name = f"{archive_root}/{relative}"
                expected_names.add(full_name)
                info = archive.getinfo(full_name) if full_name in names else None
                if info is None or info.is_dir():
                    raise DistributionError(f"Falta el archivo manifestado: {relative!r}.")
                if not isinstance(item["size"], int) or item["size"] < 0:
                    raise DistributionError(f"Tamaño inválido en el manifiesto: {relative!r}.")
                if info.file_size != item["size"]:
                    raise DistributionError(f"Tamaño distinto para {relative!r}.")
                if not isinstance(item["sha256"], str) or not re.fullmatch(
                    r"[0-9a-f]{64}", item["sha256"]
                ):
                    raise DistributionError(f"SHA-256 inválido para {relative!r}.")
                if _sha256(archive.read(full_name)) != item["sha256"]:
                    raise DistributionError(f"SHA-256 distinto para {relative!r}.")

            missing_required = sorted(REQUIRED_FILES - manifested_paths)
            if missing_required:
                raise DistributionError(
                    f"Faltan archivos operativos: {', '.join(missing_required)}."
                )
            for directory in EMPTY_DIRECTORIES:
                directory_name = f"{archive_root}/{directory}"
                expected_names.add(directory_name)
                if directory_name not in names or not archive.getinfo(directory_name).is_dir():
                    raise DistributionError(f"Falta la carpeta vacía {directory!r}.")
                if archive.getinfo(directory_name).file_size != 0:
                    raise DistributionError(f"La carpeta {directory!r} no está vacía.")
            if names != expected_names:
                raise DistributionError(
                    "El ZIP no coincide con el contenido exacto del manifiesto."
                )
            return manifest
    except BadZipFile as exc:
        raise DistributionError(f"El archivo no es un ZIP válido: {path}.") from exc


def build_archive(
    repo_root: Path,
    output: Path,
    *,
    git_executable: str | None = None,
) -> BuildResult:
    root = _repository_root(repo_root, git_executable)
    _assert_clean(root, git_executable)
    entries = _tree_entries(root, git_executable)
    commit = _git(root, "rev-parse", "HEAD", git_executable=git_executable).decode().strip()
    commit_timestamp = int(
        _git(root, "show", "-s", "--format=%ct", "HEAD", git_executable=git_executable)
        .decode()
        .strip()
    )

    destination = output.resolve()
    if destination.suffix.casefold() != ".zip":
        raise DistributionError("El artefacto de salida debe terminar en .zip.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.stem}-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        archive_root, file_count = _archive_bytes(
            root,
            entries,
            commit,
            commit_timestamp,
            git_executable,
            temporary_path,
        )
        verify_archive(temporary_path)
        digest = _sha256(temporary_path.read_bytes())
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return BuildResult(destination, archive_root, commit, file_count, digest)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Construye o verifica la distribución portable de ELAN Quantum."
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output", type=Path, help="Construye un ZIP desde el HEAD limpio.")
    action.add_argument("--verify", type=Path, help="Verifica un ZIP sin extraerlo.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.verify:
            manifest = verify_archive(args.verify)
            print(
                f"[OK] ZIP válido: {args.verify.resolve()} | "
                f"{len(manifest['files'])} archivos | commit {manifest['commit']}"
            )
        else:
            result = build_archive(args.repo_root, args.output)
            print(
                f"[OK] ZIP creado y verificado: {result.output} | "
                f"{result.file_count} archivos | SHA-256 {result.sha256}"
            )
    except (DistributionError, OSError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
