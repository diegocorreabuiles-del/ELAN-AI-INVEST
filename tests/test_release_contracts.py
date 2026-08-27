from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ci_uses_recovered_git_and_lock_gates() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert '"recovery/**"' in workflow
    assert "actions/checkout@v7" in workflow
    assert "actions/setup-python@v7" in workflow
    assert "python scripts/check_git_flow.py" in workflow
    assert "python scripts/check_module_lifecycle.py" in workflow
    assert "python -m pip install -r requirements.txt" in workflow
    assert "python -m pip install --no-deps --no-build-isolation -e .[dev]" in workflow
    assert "python scripts/check_lock.py" in workflow
    assert "python scripts/build_distribution.py --output dist/elan-quantum-ci.zip" in workflow
    assert "python scripts/build_distribution.py --verify dist/elan-quantum-ci.zip" in workflow
    assert workflow.index("python -m pip install -r requirements.txt") < workflow.index(
        "python scripts/check_lock.py"
    )


def test_installers_validate_lock_and_environment() -> None:
    for filename in ("install.bat", "update.bat"):
        content = (ROOT / filename).read_text(encoding="utf-8")
        lock_install_index = content.index("python -m pip install -r requirements.txt")
        project_install_index = content.index(
            "python -m pip install --no-deps --no-build-isolation -e .[dev]"
        )
        lock_index = content.index("python scripts\\check_lock.py")
        pip_check_index = content.index("python -m pip check")

        assert lock_install_index < project_install_index < lock_index < pip_check_index


def test_documented_release_tooling_paths_exist() -> None:
    for relative_path in (
        "GIT_WORKFLOW.md",
        "requirements.lock",
        "scripts/check_git_flow.py",
        "scripts/check_lock.py",
        "scripts/generate_hashed_lock.py",
        "scripts/build_distribution.py",
        "scripts/run_ci_matrix.ps1",
    ):
        assert (ROOT / relative_path).is_file(), relative_path


def test_local_ci_matrix_is_isolated_and_matches_github_versions() -> None:
    script = (ROOT / "scripts" / "run_ci_matrix.ps1").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    for version in ("3.11", "3.12", "3.13", "3.14"):
        assert f'"{version}"' in script
        assert f'"{version}"' in workflow

    assert "target=/workspace,readonly" in script
    assert "PYTHONDONTWRITEBYTECODE=1" in script
    assert "COVERAGE_FILE=/tmp/.coverage" in script
    assert "python scripts/check_lock.py" in script
    assert "python -m pytest -p no:cacheprovider" in script
    assert "python scripts/build_distribution.py --verify" in script


def test_ci_audits_locked_dependencies_with_pinned_action() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "pypa/gh-action-pip-audit@1220774d901786e6f652ae159f7b6bc8fea6d266" in workflow
    assert "inputs: requirements.lock" in workflow
    assert "no-deps: true" in workflow
    assert "internal-be-careful-allow-failure" not in workflow


def test_mypy_gate_covers_the_complete_package_tree() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"src/elan_ai_invest"' in pyproject
    assert "exclude =" not in pyproject


def test_audited_dependency_pins_are_synchronized() -> None:
    lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    assert "gitpython==3.1.59" in lock
    assert "pip==26.2.1" in lock

    for relative_path in (
        ".github/workflows/ci.yml",
        "scripts/run_ci_matrix.ps1",
        "install.bat",
        "update.bat",
    ):
        content = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "-r requirements.txt" in content, relative_path
        assert "--no-deps --no-build-isolation -e .[dev]" in content, relative_path
        assert "pip install --upgrade" not in content, relative_path
