from __future__ import annotations

import argparse
import re
import sys
import tomllib
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

PROJECT_NAME = canonicalize_name("elan-ai-invest")
HASH_PATTERN = re.compile(r"--hash=sha256:([0-9a-fA-F]{64})(?=\s|$)")
SUPPORTED_MIN = (3, 11)
SUPPORTED_MAX = (3, 15)


class LockError(ValueError):
    """Raised when the dependency lock and the active environment disagree."""


@dataclass(frozen=True)
class LockEntry:
    requirement: Requirement
    hashes: tuple[str, ...]
    line_number: int


def _lock_blocks(path: Path) -> Iterator[tuple[int, str]]:
    parts: list[str] = []
    start_line = 0
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            if parts:
                raise LockError(f"{path}:{start_line} contiene una continuación incompleta.")
            continue
        if not parts:
            start_line = line_number
        continued = line.endswith("\\")
        parts.append(line[:-1].rstrip() if continued else line)
        if continued:
            continue
        yield start_line, " ".join(parts)
        parts = []
    if parts:
        raise LockError(f"{path}:{start_line} contiene una continuación incompleta.")


def read_lock_entries(path: Path, require_hashes: bool = True) -> tuple[LockEntry, ...]:
    if not path.is_file():
        raise LockError(f"No existe el lock: {path}")
    entries: list[LockEntry] = []
    for line_number, block in _lock_blocks(path):
        if block.startswith(("-c ", "-r ", "-e ", "--")):
            raise LockError(f"{path}:{line_number} no es un pin de dependencia: {block}")
        hashes = tuple(digest.lower() for digest in HASH_PATTERN.findall(block))
        requirement_text = HASH_PATTERN.sub("", block).strip()
        if "--hash" in requirement_text:
            raise LockError(f"{path}:{line_number} contiene un hash SHA-256 no válido.")
        if require_hashes and not hashes:
            raise LockError(f"{path}:{line_number} no contiene hash SHA-256.")
        if len(hashes) != len(set(hashes)):
            raise LockError(f"{path}:{line_number} contiene hashes duplicados.")
        try:
            requirement = Requirement(requirement_text)
        except InvalidRequirement as exc:
            raise LockError(f"{path}:{line_number} no es válido: {requirement_text}") from exc
        exact_pin(requirement)
        entries.append(LockEntry(requirement, hashes, line_number))
    if not entries:
        raise LockError(f"El lock no contiene pins: {path}")
    return tuple(entries)


def marker_environment(overrides: Mapping[str, str] | None = None) -> dict[str, str]:
    environment = default_environment()
    if overrides:
        environment.update(overrides)
    return environment


def exact_pin(requirement: Requirement) -> str:
    specifiers = list(requirement.specifier)
    if len(specifiers) != 1 or specifiers[0].operator != "==":
        raise LockError(f"{requirement} no contiene un único pin exacto con ==.")
    version = specifiers[0].version
    if "*" in version:
        raise LockError(f"{requirement} usa un pin comodín, que no es reproducible.")
    if requirement.url:
        raise LockError(f"{requirement} usa una URL en vez de una versión fijada.")
    return version


def parse_lock(
    path: Path,
    environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    active_environment = marker_environment(environment)
    pins: dict[str, str] = {}
    for entry in read_lock_entries(path):
        requirement = entry.requirement
        version = exact_pin(requirement)
        if requirement.marker and not requirement.marker.evaluate(active_environment):
            continue
        name = canonicalize_name(requirement.name)
        if name in pins:
            raise LockError(f"Pin activo duplicado para {name} en {path}:{entry.line_number}.")
        pins[name] = version

    if not pins:
        raise LockError(f"El lock no contiene pins activos para este entorno: {path}")
    return pins


def _active_requirement_names(
    raw_requirements: Sequence[str],
    environment: Mapping[str, str],
) -> set[str]:
    names: set[str] = set()
    for raw_requirement in raw_requirements:
        requirement = Requirement(raw_requirement)
        if requirement.marker and not requirement.marker.evaluate(environment):
            continue
        names.add(canonicalize_name(requirement.name))
    return names


def declared_dependencies(
    pyproject_path: Path,
    environment: Mapping[str, str] | None = None,
) -> tuple[set[str], list[str]]:
    if not pyproject_path.is_file():
        raise LockError(f"No existe pyproject.toml: {pyproject_path}")
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    active_environment = marker_environment(environment)
    project = data.get("project", {})
    raw_requirements = list(project.get("dependencies", []))
    optional = project.get("optional-dependencies", {})
    raw_requirements.extend(optional.get("dev", []))
    names = _active_requirement_names(raw_requirements, active_environment)
    build_requirements = list(data.get("build-system", {}).get("requires", []))
    return names, build_requirements


def validate_build_requirements(raw_requirements: Sequence[str]) -> set[str]:
    if not raw_requirements:
        raise LockError("pyproject.toml no declara la cadena de build.")
    names: set[str] = set()
    for raw_requirement in raw_requirements:
        requirement = Requirement(raw_requirement)
        exact_pin(requirement)
        names.add(canonicalize_name(requirement.name))
    return names


def validate_requirements_contract(path: Path) -> None:
    if not path.is_file():
        raise LockError(f"No existe requirements.txt: {path}")
    lines = {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if "--require-hashes" not in lines:
        raise LockError("requirements.txt debe exigir --require-hashes.")
    if "-r requirements.lock" not in lines:
        raise LockError("requirements.txt debe instalar -r requirements.lock.")
    if any(line.startswith("-e ") for line in lines):
        raise LockError("El proyecto editable debe instalarse aparte con --no-deps.")


def installed_versions() -> dict[str, str]:
    installed: dict[str, str] = {}
    for distribution in metadata.distributions():
        name = distribution.metadata.get("Name")
        if name:
            installed[canonicalize_name(name)] = distribution.version
    return installed


def validate_environment(
    pins: Mapping[str, str],
    declared: set[str],
    installed: Mapping[str, str],
) -> tuple[int, int]:
    missing_declared = sorted(name for name in declared if name not in installed)
    if missing_declared:
        raise LockError(f"Dependencias directas no instaladas: {', '.join(missing_declared)}")

    missing_pins = sorted(name for name in declared if name not in pins)
    if missing_pins:
        raise LockError(f"Dependencias directas sin pin activo: {', '.join(missing_pins)}")

    compared = 0
    for name, installed_version in sorted(installed.items()):
        if name == PROJECT_NAME:
            continue
        if name not in pins:
            raise LockError(f"Distribución instalada sin pin activo: {name}=={installed_version}")
        expected = pins[name]
        if installed_version != expected:
            raise LockError(
                f"Versión distinta para {name}: instalada {installed_version}, lock {expected}."
            )
        compared += 1
    return len(pins), compared


def validate_supported_python() -> None:
    current = sys.version_info[:2]
    if current < SUPPORTED_MIN or current >= SUPPORTED_MAX:
        raise LockError(
            "Este lock solo admite Python 3.11-3.14; "
            f"el intérprete actual es {current[0]}.{current[1]}."
        )


def validate(root: Path) -> tuple[int, int]:
    validate_supported_python()
    active_environment = marker_environment()
    pins = parse_lock(root / "requirements.lock", active_environment)
    declared, build_requirements = declared_dependencies(
        root / "pyproject.toml", active_environment
    )
    declared.update(validate_build_requirements(build_requirements))
    validate_requirements_contract(root / "requirements.txt")
    return validate_environment(pins, declared, installed_versions())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida el lock reproducible de ELAN Quantum.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        active_pins, compared = validate(args.root.resolve())
    except LockError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    print(
        f"[OK] Lock válido: {active_pins} pins activos; "
        f"{compared} distribuciones instaladas verificadas."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
