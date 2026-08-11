from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    symbol TEXT NOT NULL,
    price REAL,
    score REAL,
    confidence REAL,
    signal TEXT,
    return_1m_pct REAL,
    return_3m_pct REAL,
    volatility_pct REAL,
    drawdown_pct REAL
);
CREATE TABLE IF NOT EXISTS workspace_preferences (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    symbols_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.executescript(SCHEMA)


def save_snapshot(path: Path, ranking: pd.DataFrame, captured_at: str) -> int:
    if ranking.empty:
        return 0
    init_db(path)
    columns = [
        "symbol",
        "price",
        "score",
        "confidence",
        "signal",
        "return_1m_pct",
        "return_3m_pct",
        "volatility_pct",
        "drawdown_pct",
    ]
    payload = ranking[columns].copy()
    payload.insert(0, "captured_at", captured_at)
    with closing(sqlite3.connect(path)) as conn, conn:
        payload.to_sql("analysis_history", conn, if_exists="append", index=False)
    return len(payload)


def read_history(path: Path, limit: int = 500) -> pd.DataFrame:
    init_db(path)
    with closing(sqlite3.connect(path)) as conn, conn:
        return pd.read_sql_query(
            "SELECT * FROM analysis_history ORDER BY captured_at DESC, score DESC LIMIT ?",
            conn,
            params=(limit,),
        )


def _normalize_workspace_symbols(symbols: Sequence[object]) -> list[str]:
    normalized = (str(symbol).strip().upper() for symbol in symbols)
    return list(dict.fromkeys(symbol for symbol in normalized if symbol))


def load_workspace_symbols(path: Path) -> list[str] | None:
    init_db(path)
    with closing(sqlite3.connect(path)) as conn, conn:
        row = conn.execute("SELECT symbols_json FROM workspace_preferences WHERE id = 1").fetchone()
    if row is None:
        return None
    try:
        symbols = json.loads(row[0])
    except json.JSONDecodeError as exc:
        raise ValueError("La lista persistida de instrumentos no es JSON valido") from exc
    if not isinstance(symbols, list) or not all(isinstance(symbol, str) for symbol in symbols):
        raise ValueError("La lista persistida de instrumentos tiene un formato invalido")
    return _normalize_workspace_symbols(symbols)


def save_workspace_symbols(path: Path, symbols: Sequence[object]) -> list[str]:
    normalized = _normalize_workspace_symbols(symbols)
    init_db(path)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT INTO workspace_preferences (id, symbols_json, updated_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                symbols_json = excluded.symbols_json,
                updated_at = excluded.updated_at
            """,
            (
                json.dumps(normalized, ensure_ascii=False),
                datetime.now(UTC).isoformat(timespec="seconds"),
            ),
        )
    return normalized
