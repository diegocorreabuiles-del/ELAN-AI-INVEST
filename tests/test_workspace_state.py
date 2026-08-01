from __future__ import annotations

import pytest

import elan_ai_invest.dashboard.workspace as workspace
from elan_ai_invest.dashboard.workspace import (
    ACTIVE_SYMBOL_KEY,
    ensure_active_symbol,
    resolve_active_symbol,
    selected_symbol_from_table_state,
    set_active_symbol,
    symbol_options,
    sync_widget_to_active,
)


def test_symbol_options_normalizes_and_deduplicates() -> None:
    assert symbol_options([" aapl ", "MSFT", "aapl", ""]) == ["AAPL", "MSFT"]


def test_resolve_active_symbol_prefers_explicit_valid_symbol() -> None:
    assert resolve_active_symbol(["AAPL", "MSFT"], current="AAPL", preferred="msft") == "MSFT"


def test_resolve_active_symbol_falls_back_deterministically() -> None:
    assert resolve_active_symbol(["MSFT", "AAPL"], current="NVDA") == "MSFT"
    assert resolve_active_symbol([], current="AAPL") is None


def test_ensure_active_symbol_initializes_and_repairs_state() -> None:
    state: dict[str, object] = {}

    assert ensure_active_symbol(state, ["AAPL", "MSFT"], preferred="MSFT") == "MSFT"
    assert state[ACTIVE_SYMBOL_KEY] == "MSFT"
    assert ensure_active_symbol(state, ["AAPL"]) == "AAPL"
    assert state[ACTIVE_SYMBOL_KEY] == "AAPL"


def test_set_active_symbol_rejects_symbols_outside_workspace() -> None:
    state: dict[str, object] = {ACTIVE_SYMBOL_KEY: "AAPL"}

    assert set_active_symbol(state, "NVDA", ["AAPL", "MSFT"]) == "AAPL"
    assert state[ACTIVE_SYMBOL_KEY] == "AAPL"


def test_sync_widget_to_active_updates_stale_widget_before_render() -> None:
    state: dict[str, object] = {
        ACTIVE_SYMBOL_KEY: "MSFT",
        "fundamental_symbol": "AAPL",
    }

    assert sync_widget_to_active(state, "fundamental_symbol", ["AAPL", "MSFT"]) == "MSFT"
    assert state["fundamental_symbol"] == "MSFT"


@pytest.mark.parametrize(
    ("table_state", "expected"),
    [
        ({"selection": {"rows": [1]}}, "MSFT"),
        ({"selection": {"rows": []}}, None),
        ({"selection": {"rows": [8]}}, None),
        ({}, None),
    ],
)
def test_selected_symbol_from_table_state(table_state, expected) -> None:
    assert selected_symbol_from_table_state(table_state, ["AAPL", "MSFT"]) == expected


def test_table_callback_promotes_selected_row_to_active_symbol(monkeypatch) -> None:
    state = {"ranking_asset_table": {"selection": {"rows": [1]}}}
    monkeypatch.setattr(workspace.st, "session_state", state)

    workspace.activate_from_table("ranking_asset_table", ("AAPL", "MSFT"))

    assert state[ACTIVE_SYMBOL_KEY] == "MSFT"


def test_widget_callback_promotes_widget_value_to_active_symbol(monkeypatch) -> None:
    state = {"fundamental_symbol": "MSFT", ACTIVE_SYMBOL_KEY: "AAPL"}
    monkeypatch.setattr(workspace.st, "session_state", state)

    workspace.activate_from_widget("fundamental_symbol", ("AAPL", "MSFT"))

    assert state[ACTIVE_SYMBOL_KEY] == "MSFT"
