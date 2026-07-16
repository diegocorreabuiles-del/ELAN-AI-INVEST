"""Canonical backtesting package."""

from .engine import BacktestEngine
from .momentum import momentum_backtest, performance_stats

__all__ = ["BacktestEngine", "momentum_backtest", "performance_stats"]
