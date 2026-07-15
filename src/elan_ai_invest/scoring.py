from __future__ import annotations

import numpy as np
import pandas as pd


def _safe_return(series: pd.Series, periods: int) -> float:
    clean = series.dropna()
    if len(clean) <= periods:
        return np.nan
    return float(clean.iloc[-1] / clean.iloc[-periods - 1] - 1)


def score_assets(prices: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []

    for symbol in prices.columns:
        series = prices[symbol].dropna()
        if len(series) < 210:
            continue

        last = float(series.iloc[-1])
        ma50 = float(series.tail(50).mean())
        ma200 = float(series.tail(200).mean())
        ret_1m = _safe_return(series, 21)
        ret_3m = _safe_return(series, 63)
        ret_6m = _safe_return(series, 126)
        daily = series.pct_change().dropna()
        volatility = float(daily.tail(63).std() * np.sqrt(252))

        trend_score = 50.0
        trend_score += 25.0 if last > ma50 else -25.0
        trend_score += 25.0 if ma50 > ma200 else -25.0

        momentum_raw = np.nanmean([ret_1m, ret_3m, ret_6m])
        momentum_score = float(np.clip(50 + momentum_raw * 180, 0, 100))
        risk_score = float(np.clip(100 - volatility * 140, 0, 100))
        total = 0.45 * trend_score + 0.35 * momentum_score + 0.20 * risk_score

        if total >= 70:
            signal = "Fuerte"
        elif total >= 58:
            signal = "Positiva"
        elif total >= 42:
            signal = "Neutral"
        else:
            signal = "Debil"

        rows.append(
            {
                "symbol": symbol,
                "price": last,
                "score": round(float(total), 1),
                "signal": signal,
                "return_1m_pct": round(ret_1m * 100, 2),
                "return_3m_pct": round(ret_3m * 100, 2),
                "return_6m_pct": round(ret_6m * 100, 2),
                "volatility_pct": round(volatility * 100, 2),
            }
        )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
