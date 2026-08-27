from __future__ import annotations

import numpy as np
import pandas as pd

from .benchmark import build_benchmark_curve
from .costs import apply_transaction_costs
from .metrics import calculate_metrics
from .report import BacktestReport, build_report
from .strategy import run_strategy


class BacktestEngine:
    def run(self, prices: pd.Series, signals: pd.Series) -> BacktestReport:
        equity = run_strategy(prices, signals)
        return build_report(equity, calculate_metrics(equity))

    def run_momentum(
        self,
        prices: pd.DataFrame,
        lookback: int = 63,
        top_n: int = 3,
        rebalance: int = 21,
        *,
        commission_pct: float = 0.0,
        slippage_pct: float = 0.0,
        benchmark_symbol: str | None = None,
    ) -> pd.DataFrame:
        """Run the canonical multi-asset, long-only momentum simulation.

        Signals are calculated with closing prices and shifted one complete
        bar before execution. Costs are charged on executed turnover.
        """
        if lookback < 1 or top_n < 1 or rebalance < 1:
            raise ValueError("Lookback, top_n y rebalance deben ser positivos")

        clean = prices.dropna(how="all").ffill()
        benchmark, benchmark_label = build_benchmark_curve(clean, benchmark_symbol)
        if clean.empty or len(clean) <= lookback + rebalance:
            return pd.DataFrame()

        daily_returns = clean.pct_change().fillna(0.0)
        momentum = clean.pct_change(lookback)
        target_weights = pd.DataFrame(0.0, index=clean.index, columns=clean.columns)
        for index in range(lookback, len(clean), rebalance):
            scores = momentum.iloc[index].dropna().sort_values(ascending=False)
            selected = scores[scores > 0].head(top_n).index
            if len(selected) == 0:
                continue
            end = min(index + rebalance, len(clean))
            target_weights.loc[clean.index[index:end], selected] = 1.0 / len(selected)

        executed_weights = target_weights.shift(1).fillna(0.0)
        gross_returns = (executed_weights * daily_returns).sum(axis=1)
        net_returns, transaction_cost, turnover = apply_transaction_costs(
            gross_returns,
            executed_weights,
            commission_pct=commission_pct,
            slippage_pct=slippage_pct,
        )
        result = pd.DataFrame(
            {
                "strategy": (1.0 + net_returns).cumprod(),
                "strategy_gross": (1.0 + gross_returns).cumprod(),
                "benchmark": benchmark,
                "turnover": turnover,
                "transaction_cost": transaction_cost,
            }
        )
        if benchmark_symbol is None:
            result["benchmark_equal_weight"] = benchmark
        result.attrs.update(
            {
                "benchmark_symbol": benchmark_label,
                "commission_pct": float(commission_pct),
                "slippage_pct": float(slippage_pct),
                "execution_lag_bars": 1,
            }
        )
        return result

    @staticmethod
    def performance_stats(equity: pd.Series) -> dict[str, float]:
        """Return the metrics consumed by the Streamlit backtesting view."""
        if equity.empty or len(equity) < 2:
            return {}
        returns = equity.pct_change().dropna()
        years = len(returns) / 252
        total_return = float(equity.iloc[-1] / equity.iloc[0] - 1)
        cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1) if years > 0 else 0.0
        volatility = float(returns.std() * np.sqrt(252))
        sharpe = (
            float((returns.mean() / returns.std()) * np.sqrt(252)) if returns.std() > 0 else 0.0
        )
        drawdown = equity / equity.cummax() - 1
        return {
            "total_return_pct": total_return * 100,
            "cagr_pct": cagr * 100,
            "volatility_pct": volatility * 100,
            "sharpe": sharpe,
            "max_drawdown_pct": float(drawdown.min() * 100),
        }
