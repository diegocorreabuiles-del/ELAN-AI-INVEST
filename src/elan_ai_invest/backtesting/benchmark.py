"""Benchmark helpers for canonical backtests."""

from __future__ import annotations

import pandas as pd


def build_benchmark_curve(prices: pd.DataFrame, symbol: str | None) -> tuple[pd.Series, str]:
    """Build a normalized benchmark curve from a configured symbol."""
    if symbol:
        normalized_symbol = symbol.strip().upper()
        if normalized_symbol not in prices.columns:
            raise ValueError(
                f"El benchmark configurado '{normalized_symbol}' no está disponible "
                "en los datos del análisis"
            )
        benchmark_returns = prices[normalized_symbol].astype(float).ffill().pct_change().fillna(0.0)
        label = normalized_symbol
    else:
        benchmark_returns = prices.pct_change().fillna(0.0).mean(axis=1)
        label = "equal_weight"

    return (1.0 + benchmark_returns).cumprod(), label


def compare_against_benchmark(strategy, benchmark):
    strategy_return = float(strategy.iloc[-1] / strategy.iloc[0] - 1)
    benchmark_return = float(benchmark.iloc[-1] / benchmark.iloc[0] - 1)
    return {
        "strategy_return": strategy_return,
        "benchmark_return": benchmark_return,
        "alpha": strategy_return - benchmark_return,
    }
