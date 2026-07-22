from __future__ import annotations

import platform
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from elan_ai_invest import __version__
from elan_ai_invest.core.config import Settings

HISTORY_TABLES = frozenset({"analysis_history"})
PAPER_TABLES = frozenset(
    {"paper_account", "paper_positions", "paper_orders", "paper_equity_snapshots"}
)
_PROBE_TABLE = "__elan_ai_invest_healthcheck_probe"


@dataclass(frozen=True)
class SystemStatus:
    version: str
    python_version: str
    operating_system: str
    environment: str
    market_provider: str
    checks: dict[str, bool]

    @property
    def ok(self) -> bool:
        return all(self.checks.values())

    def as_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"comprobación": name, "estado": "OK" if passed else "PENDIENTE"}
                for name, passed in self.checks.items()
            ]
        )


def _sqlite_database_is_healthy(path: Path, required_tables: frozenset[str]) -> bool:
    if not path.is_file():
        return False
    try:
        with closing(sqlite3.connect(path, timeout=1.0, isolation_level=None)) as connection:
            integrity = connection.execute("PRAGMA quick_check").fetchone()
            if integrity != ("ok",):
                return False
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if not required_tables.issubset(tables) or _PROBE_TABLE in tables:
                return False

            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(f'CREATE TABLE "{_PROBE_TABLE}" (value INTEGER NOT NULL)')
                connection.execute(f'INSERT INTO "{_PROBE_TABLE}" VALUES (1)')
            finally:
                connection.rollback()
            return True
    except sqlite3.Error:
        return False


def collect_system_status(root: Path, settings: Settings) -> SystemStatus:
    history_path = root / settings.storage.database_path
    paper_path = root / settings.paper_trading.database_path
    checks = {
        "Configuración": (root / "config" / "settings.yaml").exists(),
        "Watchlist": (root / "config" / "watchlist.csv").exists(),
        "Carpeta de datos": (root / "data").exists(),
        "Carpeta de logs": (root / "logs").exists(),
        "Base histórica accesible": _sqlite_database_is_healthy(history_path, HISTORY_TABLES),
        "Base paper trading accesible": _sqlite_database_is_healthy(paper_path, PAPER_TABLES),
    }
    return SystemStatus(
        version=__version__,
        python_version=".".join(map(str, sys.version_info[:3])),
        operating_system=platform.platform(),
        environment=settings.app.environment,
        market_provider=settings.market.provider,
        checks=checks,
    )
