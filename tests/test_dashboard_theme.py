from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_trading_workspace_theme_uses_accessible_dark_palette() -> None:
    with (ROOT / ".streamlit" / "config.toml").open("rb") as config_file:
        theme = tomllib.load(config_file)["theme"]

    assert theme["base"] == "dark"
    assert theme["backgroundColor"] == "#0F141A"
    assert theme["secondaryBackgroundColor"] == "#181E26"
    assert theme["textColor"] == "#F2F5F7"
    assert theme["primaryColor"] == "#0F8F6F"
    assert theme["greenColor"] == "#21C994"
    assert theme["redColor"] == "#FF5C70"
    assert theme["showWidgetBorder"] is True
    assert theme["showSidebarBorder"] is True


def test_sidebar_is_visually_distinct_from_the_trading_canvas() -> None:
    with (ROOT / ".streamlit" / "config.toml").open("rb") as config_file:
        theme = tomllib.load(config_file)["theme"]

    assert theme["sidebar"]["backgroundColor"] == "#0B0F14"
    assert theme["sidebar"]["backgroundColor"] != theme["backgroundColor"]
