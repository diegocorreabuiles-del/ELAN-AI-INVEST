from __future__ import annotations

import importlib


def test_public_packages_import_without_optional_network_calls():
    modules = [
        "elan_ai_invest",
        "elan_ai_invest.market",
        "elan_ai_invest.fundamental",
    ]

    for module in modules:
        assert importlib.import_module(module) is not None


def test_version_is_stability_release():
    from elan_ai_invest import __version__

    assert __version__ == "1.2.1"
