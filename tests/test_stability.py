from __future__ import annotations

import importlib
import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from elan_ai_invest.core.config import AppConfig, load_settings


def test_public_packages_import_without_optional_network_calls():
    modules = [
        "elan_ai_invest",
        "elan_ai_invest.market",
        "elan_ai_invest.fundamental",
    ]

    for module in modules:
        assert importlib.import_module(module) is not None


def test_version_is_v1_3_release_candidate():
    from elan_ai_invest import __version__

    assert __version__ == "1.3.0rc1"


def test_release_version_is_synchronised():
    from elan_ai_invest import __version__

    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    settings = load_settings(root / "config" / "settings.yaml")

    assert project["project"]["version"] == __version__
    assert settings.app.version == __version__


def test_explicit_stale_version_is_rejected():
    with pytest.raises(ValidationError, match="debe coincidir con el paquete"):
        AppConfig(version="1.2.1")
