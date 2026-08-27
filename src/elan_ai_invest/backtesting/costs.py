"""Transaction-cost calculations for canonical backtests."""

from __future__ import annotations

import pandas as pd


def apply_costs(returns: pd.Series, commission: float = 0.001) -> pd.Series:
    """Legacy helper retained for compatibility with external callers."""
    return returns - commission


def apply_transaction_costs(
    gross_returns: pd.Series,
    executed_weights: pd.DataFrame,
    *,
    commission_pct: float = 0.0,
    slippage_pct: float = 0.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Deduct commission and slippage only when the portfolio trades.

    Percentages are charged per unit of traded notional. A full switch from
    one asset to another has turnover 2.0 because it includes a sale and a buy.
    """
    if commission_pct < 0 or slippage_pct < 0:
        raise ValueError("La comisión y el slippage no pueden ser negativos")

    weights = executed_weights.reindex(gross_returns.index).fillna(0.0)
    previous_weights = weights.shift(1).fillna(0.0)
    turnover = (weights - previous_weights).abs().sum(axis=1)
    cost_rate = (float(commission_pct) + float(slippage_pct)) / 100.0
    transaction_cost = turnover * cost_rate
    net_returns = gross_returns.astype(float) - transaction_cost
    return net_returns, transaction_cost, turnover
