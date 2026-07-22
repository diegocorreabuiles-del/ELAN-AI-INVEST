import sqlite3
from pathlib import Path

from elan_ai_invest.core.config import Settings
from elan_ai_invest.paper_trading import PaperTradingEngine
from elan_ai_invest.storage import init_db
from elan_ai_invest.system_status import collect_system_status


def test_system_status_reports_required_files(tmp_path: Path):
    (tmp_path / "config").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "config" / "settings.yaml").write_text("app: {}", encoding="utf-8")
    (tmp_path / "config" / "watchlist.csv").write_text(
        "symbol,name\nSPY,S&P 500\n", encoding="utf-8"
    )
    settings = Settings()
    init_db(tmp_path / settings.storage.database_path)
    PaperTradingEngine(
        tmp_path / settings.paper_trading.database_path,
        initial_capital=settings.paper_trading.initial_capital,
        commission_pct=settings.paper_trading.commission_pct,
        stop_loss_pct=settings.paper_trading.stop_loss_pct,
        max_open_positions=settings.paper_trading.max_open_positions,
    )

    status = collect_system_status(tmp_path, settings)
    assert status.ok
    assert status.version == "1.2.2"
    with sqlite3.connect(tmp_path / settings.storage.database_path) as connection:
        probe = connection.execute(
            "SELECT name FROM sqlite_master WHERE name = '__elan_ai_invest_healthcheck_probe'"
        ).fetchone()
    assert probe is None


def test_system_status_rejects_missing_or_incomplete_databases(tmp_path: Path):
    (tmp_path / "config").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "config" / "settings.yaml").write_text("app: {}", encoding="utf-8")
    (tmp_path / "config" / "watchlist.csv").write_text(
        "symbol,name\nSPY,S&P 500\n", encoding="utf-8"
    )
    settings = Settings()

    missing = collect_system_status(tmp_path, settings)
    assert not missing.checks["Base histórica accesible"]
    assert not missing.checks["Base paper trading accesible"]

    (tmp_path / settings.storage.database_path).touch()
    incomplete = collect_system_status(tmp_path, settings)
    assert not incomplete.checks["Base histórica accesible"]

    (tmp_path / settings.storage.database_path).write_bytes(b"not-a-sqlite-database")
    corrupt = collect_system_status(tmp_path, settings)
    assert not corrupt.checks["Base histórica accesible"]
