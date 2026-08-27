from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_git_flow import FlowError, normalize_branch, run, validate_transition
from scripts.check_lock import (
    LockError,
    parse_lock,
    validate_environment,
    validate_requirements_contract,
)

ROOT = Path(__file__).resolve().parents[1]
HASH_ZERO = "0" * 64
HASH_ONE = "1" * 64


@pytest.mark.parametrize(
    "head",
    [
        "feature/new-screen",
        "fix/cache-race",
        "chore/lock-refresh",
        "docs/install-guide",
        "recovery/pc-migration",
        "dependabot/pip/pytest-9.1.1",
    ],
)
def test_work_branches_can_target_develop(head: str) -> None:
    validate_transition(head, "develop")


def test_develop_can_target_main() -> None:
    validate_transition("develop", "main")


@pytest.mark.parametrize(
    ("head", "base"),
    [
        ("feature/new-screen", "main"),
        ("main", "develop"),
        ("develop", "feature/new-screen"),
        ("unknown/topic", "develop"),
    ],
)
def test_invalid_transitions_are_rejected(head: str, base: str) -> None:
    with pytest.raises(FlowError):
        validate_transition(head, base)


def test_remote_refs_are_normalized() -> None:
    assert normalize_branch("refs/heads/feature/demo") == "feature/demo"
    assert normalize_branch("refs/remotes/origin/develop") == "develop"
    assert normalize_branch("origin/main") == "main"


def test_pull_request_context_is_read_from_github_environment(tmp_path) -> None:
    message = run(
        ["--repo-root", str(tmp_path)],
        environ={
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_HEAD_REF": "fix/cache-race",
            "GITHUB_BASE_REF": "develop",
        },
    )

    assert message == "Flujo válido: fix/cache-race -> develop"


def test_pull_request_requires_a_base(tmp_path) -> None:
    with pytest.raises(FlowError, match="rama base"):
        run(
            ["--repo-root", str(tmp_path)],
            environ={
                "GITHUB_EVENT_NAME": "pull_request",
                "GITHUB_HEAD_REF": "fix/cache-race",
            },
        )


def test_lock_selects_the_python_specific_numpy_pin(tmp_path) -> None:
    lock = tmp_path / "requirements.lock"
    lock.write_text(
        f'numpy==2.2.6 ; python_version == "3.11" --hash=sha256:{HASH_ZERO}\n'
        f'numpy==2.5.1 ; python_version >= "3.12" and python_version < "3.15" --hash=sha256:{HASH_ONE}\n',
        encoding="utf-8",
    )

    pins_311 = parse_lock(lock, {"python_version": "3.11"})
    pins_314 = parse_lock(lock, {"python_version": "3.14"})

    assert pins_311["numpy"] == "2.2.6"
    assert pins_314["numpy"] == "2.5.1"


def test_lock_rejects_non_exact_versions(tmp_path) -> None:
    lock = tmp_path / "requirements.lock"
    lock.write_text(f"pandas>=3.0 --hash=sha256:{HASH_ZERO}\n", encoding="utf-8")

    with pytest.raises(LockError, match="pin exacto"):
        parse_lock(lock)


def test_lock_rejects_missing_hash(tmp_path) -> None:
    lock = tmp_path / "requirements.lock"
    lock.write_text("pandas==3.0.3\n", encoding="utf-8")

    with pytest.raises(LockError, match="hash SHA-256"):
        parse_lock(lock)


def test_requirements_file_must_consume_hashed_lock(tmp_path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("-e .\n", encoding="utf-8")

    with pytest.raises(LockError, match="require-hashes"):
        validate_requirements_contract(requirements)


def test_environment_versions_must_match_active_pins() -> None:
    active_pins, compared = validate_environment(
        pins={"numpy": "2.5.1", "pytest": "9.1.1"},
        declared={"numpy"},
        installed={"elan-ai-invest": "1.2.2", "numpy": "2.5.1", "pytest": "9.1.1"},
    )

    assert active_pins == 2
    assert compared == 2


def test_environment_rejects_version_drift() -> None:
    with pytest.raises(LockError, match="distinta"):
        validate_environment(
            pins={"numpy": "2.5.1"},
            declared={"numpy"},
            installed={"numpy": "2.5.0"},
        )


def test_windows_updater_never_deletes_project_files() -> None:
    source = (ROOT / "update.bat").read_text(encoding="utf-8")
    assert "del /q" not in source.lower()
