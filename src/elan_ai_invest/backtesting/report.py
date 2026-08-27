from __future__ import annotations

from typing import TypedDict

import pandas as pd


class BacktestReport(TypedDict):
    equity: pd.Series
    metrics: dict[str, float]


def build_report(equity: pd.Series, metrics: dict[str, float]) -> BacktestReport:
    return {"equity": equity, "metrics": metrics}
