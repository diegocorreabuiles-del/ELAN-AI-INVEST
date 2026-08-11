from pathlib import Path

from elan_ai_invest.storage import load_workspace_symbols, save_workspace_symbols


def test_workspace_symbols_round_trip_preserves_order_and_normalizes(tmp_path: Path) -> None:
    path = tmp_path / "history.db"

    assert load_workspace_symbols(path) is None

    save_workspace_symbols(path, [" msft ", "AAPL", "msft", ""])

    assert load_workspace_symbols(path) == ["MSFT", "AAPL"]


def test_workspace_symbols_can_persist_an_empty_selection(tmp_path: Path) -> None:
    path = tmp_path / "history.db"

    save_workspace_symbols(path, [])

    assert load_workspace_symbols(path) == []
