"""Compatibility functions delegating to the canonical BacktestEngine."""

from __future__ import annotations

import pandas as pd

from .engine import BacktestEngine


def momentum_backtest(
    prices: pd.DataFrame, lookback: int = 63, top_n: int = 3, rebalance: int = 21
) -> pd.DataFrame:
    """Delegate the historical public function to the canonical engine."""
    return BacktestEngine().run_momentum(prices, lookback, top_n, rebalance)


def performance_stats(equity: pd.Series) -> dict[str, float]:
    return BacktestEngine.performance_stats(equity)
