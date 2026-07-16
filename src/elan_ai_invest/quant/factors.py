from __future__ import annotations

import numpy as np
import pandas as pd


def _safe_return(series: pd.Series, periods: int) -> float:
    if len(series) <= periods:
        return 0.0
    value = series.pct_change(periods).iloc[-1]
    return 0.0 if pd.isna(value) else float(value)


def _trend_quality(series: pd.Series) -> float:
    returns = series.pct_change().dropna().tail(126)
    if returns.empty:
        return 0.0
    positive_ratio = float((returns > 0).mean())
    consistency = 1.0 - min(float(returns.std() * np.sqrt(252)), 1.0)
    return float(np.clip((positive_ratio * 0.65 + consistency * 0.35) * 100, 0, 100))


def calculate_factor_table(
    prices: pd.DataFrame,
    benchmark: str = "SPY",
) -> pd.DataFrame:
    """Calculate reusable professional factors for each asset.

    The function uses only historical adjusted closes and is deterministic,
    making it suitable for research, ranking and unit tests.
    """

    if prices.empty:
        return pd.DataFrame()

    benchmark_series = prices[benchmark].dropna() if benchmark in prices.columns else None
    benchmark_3m = _safe_return(benchmark_series, 63) if benchmark_series is not None else 0.0
    benchmark_6m = _safe_return(benchmark_series, 126) if benchmark_series is not None else 0.0

    rows: list[dict[str, float | str]] = []
    for symbol in prices.columns:
        series = prices[symbol].dropna()
        if len(series) < 210:
            continue

        last = float(series.iloc[-1])
        ema20 = float(series.ewm(span=20, adjust=False).mean().iloc[-1])
        ema50 = float(series.ewm(span=50, adjust=False).mean().iloc[-1])
        ema200_series = series.ewm(span=200, adjust=False).mean()
        ema200 = float(ema200_series.iloc[-1])
        ema200_prev = float(ema200_series.iloc[-21])
        slope_200 = (ema200 / ema200_prev - 1.0) if ema200_prev else 0.0

        ret_1m = _safe_return(series, 21)
        ret_3m = _safe_return(series, 63)
        ret_6m = _safe_return(series, 126)
        ret_12m = _safe_return(series, 252)
        volatility = float(series.pct_change().dropna().tail(63).std() * np.sqrt(252))
        downside = series.pct_change().dropna().tail(126)
        downside_vol = (
            float(downside[downside < 0].std() * np.sqrt(252)) if (downside < 0).any() else 0.0
        )
        max_drawdown = float((series / series.cummax() - 1.0).min())

        trend_score = 0.0
        trend_score += 25 if last > ema20 else 0
        trend_score += 25 if ema20 > ema50 else 0
        trend_score += 25 if ema50 > ema200 else 0
        trend_score += 25 if slope_200 > 0 else 0

        momentum_score = float(
            np.clip(50 + ret_1m * 120 + ret_3m * 90 + ret_6m * 55 + ret_12m * 25, 0, 100)
        )
        relative_strength = float(
            np.clip(50 + (ret_3m - benchmark_3m) * 160 + (ret_6m - benchmark_6m) * 90, 0, 100)
        )
        risk_adjusted = float(np.clip(50 + (ret_6m / max(volatility, 0.05)) * 18, 0, 100))
        trend_quality = _trend_quality(series)

        rows.append(
            {
                "symbol": symbol,
                "ema20": round(ema20, 4),
                "ema50": round(ema50, 4),
                "ema200": round(ema200, 4),
                "ema200_slope_pct": round(slope_200 * 100, 2),
                "return_12m_pct": round(ret_12m * 100, 2),
                "downside_volatility_pct": round(downside_vol * 100, 2),
                "historical_max_drawdown_pct": round(max_drawdown * 100, 2),
                "trend_factor": round(trend_score, 1),
                "momentum_factor": round(momentum_score, 1),
                "relative_strength_factor": round(relative_strength, 1),
                "risk_adjusted_factor": round(risk_adjusted, 1),
                "trend_quality_factor": round(trend_quality, 1),
            }
        )

    return pd.DataFrame(rows)
