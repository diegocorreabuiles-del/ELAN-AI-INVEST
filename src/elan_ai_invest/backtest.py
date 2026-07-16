"""Compatibility adapter for the canonical :mod:`elan_ai_invest.backtesting` package.

New code must import from ``elan_ai_invest.backtesting``. This module remains
available during the v1.2 compatibility window.
"""

from elan_ai_invest.backtesting.momentum import momentum_backtest, performance_stats

__all__ = ["momentum_backtest", "performance_stats"]
