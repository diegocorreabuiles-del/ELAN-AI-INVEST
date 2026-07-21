from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest

from scripts.build_distribution import DistributionError, build_archive, verify_archive

GIT = os.environ.get("GIT_EXECUTABLE") or shutil.which("git")


def _git(root: Path, *args: str) -> None:
    if not GIT:
        pytest.skip("Git no está disponible para la prueba de distribución.")
    subprocess.run([GIT, *args], cwd=root, check=True, capture_output=True)


def _repository(root: Path) -> Path:
    repo = root / "repo"
    files = {
        "app.py": "print('ELAN Quantum')\n",
        "README.md": "# ELAN Quantum\n",
        "pyproject.toml": "[project]\nname='elan-ai-invest'\nversion='1.2.2'\n",
        "requirements.txt": "-c requirements.lock\n",
        "requirements.lock": "example==1.0.0\n",
        "run.bat": "@echo off\n",
        "install.bat": "@echo off\n",
        "update.bat": "@echo off\n",
        "config/settings.yaml": "app:\n  version: '1.2.2'\n",
        "src/elan_ai_invest/__init__.py": '__version__ = "1.2.2"\n',
        "scripts/build_distribution.py": "# packaged verifier\n",
    }
    for relative, content in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Distribution Test")
    _git(repo, "config", "user.email", "distribution@example.invalid")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "fixture")
    return repo


def _rewrite_archive(source: Path, target: Path, replacements: dict[str, bytes]) -> None:
    with ZipFile(source) as original, ZipFile(target, "w", ZIP_DEFLATED) as changed:
        for info in original.infolist():
            data = b"" if info.is_dir() else original.read(info.filename)
            changed.writestr(info, replacements.get(info.filename, data))


def test_build_is_reproducible_and_contains_only_manifested_files(tmp_path) -> None:
    repo = _repository(tmp_path)
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    first_result = build_archive(repo, first, git_executable=GIT)
    second_result = build_archive(repo, second, git_executable=GIT)
    manifest = verify_archive(first)

    assert first.read_bytes() == second.read_bytes()
    assert first_result.sha256 == second_result.sha256
    assert manifest["commit"] == first_result.commit
    assert manifest["version"] == "1.2.2"
    assert manifest["empty_directories"] == ["data/", "logs/"]

    with ZipFile(first) as archive:
        names = set(archive.namelist())
    root = manifest["root"]
    expected = {f"{root}/{item['path']}" for item in manifest["files"]}
    expected.update(
        {
            f"{root}/DISTRIBUTION_MANIFEST.json",
            f"{root}/data/",
            f"{root}/logs/",
        }
    )
    assert names == expected


def test_build_rejects_a_dirty_worktree(tmp_path) -> None:
    repo = _repository(tmp_path)
    (repo / "app.py").write_text("print('dirty')\n", encoding="utf-8")

    with pytest.raises(DistributionError, match="working tree"):
        build_archive(repo, tmp_path / "dirty.zip", git_executable=GIT)


def test_build_uses_head_and_ignores_local_ignored_state(tmp_path) -> None:
    repo = _repository(tmp_path)
    (repo / ".gitignore").write_text("local-state.db\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-q", "-m", "ignore local state")
    (repo / "local-state.db").write_bytes(b"must not ship")

    archive_path = tmp_path / "head-only.zip"
    build_archive(repo, archive_path, git_executable=GIT)
    manifest = verify_archive(archive_path)

    assert "local-state.db" not in {item["path"] for item in manifest["files"]}


def test_build_rejects_sensitive_tracked_content(tmp_path) -> None:
    repo = _repository(tmp_path)
    credential = repo / "config" / "api_token.txt"
    credential.write_text("placeholder", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "unsafe fixture")

    with pytest.raises(DistributionError, match="sensible"):
        build_archive(repo, tmp_path / "unsafe.zip", git_executable=GIT)


def test_verify_rejects_file_content_tampering(tmp_path) -> None:
    repo = _repository(tmp_path)
    original = tmp_path / "original.zip"
    tampered = tmp_path / "tampered.zip"
    build_archive(repo, original, git_executable=GIT)
    manifest = verify_archive(original)
    app_path = f"{manifest['root']}/app.py"
    with ZipFile(original) as archive:
        original_app = archive.read(app_path)
    _rewrite_archive(original, tampered, {app_path: b"X" * len(original_app)})

    with pytest.raises(DistributionError, match="SHA-256"):
        verify_archive(tampered)


def test_verify_rejects_an_unmanifested_extra_file(tmp_path) -> None:
    repo = _repository(tmp_path)
    original = tmp_path / "original.zip"
    tampered = tmp_path / "extra.zip"
    build_archive(repo, original, git_executable=GIT)
    manifest = verify_archive(original)
    _rewrite_archive(original, tampered, {})
    with ZipFile(tampered, "a", ZIP_DEFLATED) as archive:
        archive.writestr(f"{manifest['root']}/unexpected.txt", b"extra")

    with pytest.raises(DistributionError, match="contenido exacto"):
        verify_archive(tampered)


def test_verify_rejects_unsafe_archive_paths(tmp_path) -> None:
    archive_path = tmp_path / "traversal.zip"
    manifest = {
        "schema_version": 1,
        "project": "elan-ai-invest",
        "version": "1.2.2",
        "commit": "a" * 40,
        "root": "elan-quantum-1.2.2",
        "files": [],
        "empty_directories": ["data/", "logs/"],
    }
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("elan-quantum-1.2.2/../escape.txt", b"escape")
        archive.writestr(
            "elan-quantum-1.2.2/DISTRIBUTION_MANIFEST.json",
            json.dumps(manifest).encode(),
        )

    with pytest.raises(DistributionError, match="ruta insegura"):
        verify_archive(archive_path)


def test_verify_rejects_symlink_entries(tmp_path) -> None:
    archive_path = tmp_path / "symlink.zip"
    info = ZipInfo("elan-quantum-1.2.2/link")
    info.create_system = 3
    info.external_attr = 0o120777 << 16
    with ZipFile(archive_path, "w") as archive:
        archive.writestr(info, b"target")

    with pytest.raises(DistributionError, match="enlace simbólico"):
        verify_archive(archive_path)
