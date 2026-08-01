from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import streamlit as st

ACTIVE_SYMBOL_KEY = "active_symbol"


def symbol_options(values: Sequence[object]) -> list[str]:
    return list(dict.fromkeys(str(value).strip().upper() for value in values if str(value).strip()))


def resolve_active_symbol(
    symbols: Sequence[object],
    *,
    current: object | None = None,
    preferred: object | None = None,
) -> str | None:
    options = symbol_options(symbols)
    for candidate in (preferred, current):
        if candidate is None:
            continue
        normalized = str(candidate).strip().upper()
        if normalized in options:
            return normalized
    return options[0] if options else None


def ensure_active_symbol(
    state: Any,
    symbols: Sequence[object],
    *,
    preferred: object | None = None,
) -> str | None:
    active = resolve_active_symbol(
        symbols,
        current=state.get(ACTIVE_SYMBOL_KEY),
        preferred=preferred,
    )
    if active is None:
        state.pop(ACTIVE_SYMBOL_KEY, None)
    else:
        state[ACTIVE_SYMBOL_KEY] = active
    return active


def set_active_symbol(
    state: Any,
    symbol: object,
    symbols: Sequence[object],
) -> str | None:
    return ensure_active_symbol(state, symbols, preferred=symbol)


def sync_widget_to_active(
    state: Any,
    widget_key: str,
    symbols: Sequence[object],
) -> str | None:
    active = ensure_active_symbol(state, symbols)
    if active is None:
        state.pop(widget_key, None)
    elif state.get(widget_key) != active:
        state[widget_key] = active
    return active


def activate_from_widget(widget_key: str, symbols: Sequence[object]) -> None:
    set_active_symbol(st.session_state, st.session_state.get(widget_key), symbols)


def selected_symbol_from_table_state(
    table_state: Any,
    symbols: Sequence[object],
) -> str | None:
    options = symbol_options(symbols)
    selection = getattr(table_state, "selection", None)
    if selection is None and hasattr(table_state, "get"):
        selection = table_state.get("selection", {})
    rows = getattr(selection, "rows", None)
    if rows is None and hasattr(selection, "get"):
        rows = selection.get("rows", [])
    if not rows:
        return None
    index = int(rows[0])
    return options[index] if 0 <= index < len(options) else None


def activate_from_table(table_key: str, symbols: Sequence[object]) -> None:
    symbol = selected_symbol_from_table_state(st.session_state.get(table_key, {}), symbols)
    if symbol is not None:
        set_active_symbol(st.session_state, symbol, symbols)
