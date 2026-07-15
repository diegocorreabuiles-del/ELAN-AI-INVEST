from __future__ import annotations

import numpy as np
import pandas as pd


def momentum_backtest(prices: pd.DataFrame, lookback: int = 63, top_n: int = 3, rebalance: int = 21) -> pd.DataFrame:
    """Simple educational long-only momentum backtest with monthly rebalancing."""
    clean = prices.dropna(how="all").ffill()
    if clean.empty or len(clean) <= lookback + rebalance:
        return pd.DataFrame()
    daily_returns = clean.pct_change().fillna(0.0)
    momentum = clean.pct_change(lookback)
    weights = pd.DataFrame(0.0, index=clean.index, columns=clean.columns)
    for i in range(lookback, len(clean), rebalance):
        scores = momentum.iloc[i].dropna().sort_values(ascending=False)
        selected = scores[scores > 0].head(top_n).index
        if len(selected) == 0:
            continue
        end = min(i + rebalance, len(clean))
        weights.loc[clean.index[i:end], selected] = 1.0 / len(selected)
    strategy_returns = (weights.shift(1).fillna(0.0) * daily_returns).sum(axis=1)
    equity = (1.0 + strategy_returns).cumprod()
    benchmark = (1.0 + daily_returns.mean(axis=1)).cumprod()
    return pd.DataFrame({"strategy": equity, "benchmark_equal_weight": benchmark})


def performance_stats(equity: pd.Series) -> dict[str, float]:
    if equity.empty or len(equity) < 2:
        return {}
    returns = equity.pct_change().dropna()
    years = len(returns) / 252
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1)
    cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1) if years > 0 else 0.0
    volatility = float(returns.std() * np.sqrt(252))
    sharpe = float((returns.mean() / returns.std()) * np.sqrt(252)) if returns.std() > 0 else 0.0
    drawdown = equity / equity.cummax() - 1
    return {
        "total_return_pct": total_return * 100,
        "cagr_pct": cagr * 100,
        "volatility_pct": volatility * 100,
        "sharpe": sharpe,
        "max_drawdown_pct": float(drawdown.min() * 100),
    }
