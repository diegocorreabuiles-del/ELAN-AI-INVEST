from __future__ import annotations

import sqlite3
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
"""


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)


def save_snapshot(path: Path, ranking: pd.DataFrame, captured_at: str) -> int:
    if ranking.empty:
        return 0
    init_db(path)
    columns = [
        "symbol", "price", "score", "confidence", "signal", "return_1m_pct",
        "return_3m_pct", "volatility_pct", "drawdown_pct",
    ]
    payload = ranking[columns].copy()
    payload.insert(0, "captured_at", captured_at)
    with sqlite3.connect(path) as conn:
        payload.to_sql("analysis_history", conn, if_exists="append", index=False)
    return len(payload)


def read_history(path: Path, limit: int = 500) -> pd.DataFrame:
    init_db(path)
    with sqlite3.connect(path) as conn:
        return pd.read_sql_query(
            "SELECT * FROM analysis_history ORDER BY captured_at DESC, score DESC LIMIT ?",
            conn,
            params=(limit,),
        )
