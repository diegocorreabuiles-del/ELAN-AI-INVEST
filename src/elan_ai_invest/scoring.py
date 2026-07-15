from __future__ import annotations

import numpy as np
import pandas as pd


def _bounded(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return float(np.clip(value, low, high))


def _signal(score: float) -> str:
    if score >= 75:
        return "Fuerte"
    if score >= 60:
        return "Positiva"
    if score >= 45:
        return "Neutral"
    return "Debil"


def score_assets(prices: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for symbol in prices.columns:
        s = prices[symbol].dropna()
        if len(s) < 210:
            continue
        last = float(s.iloc[-1])
        ma20 = float(s.rolling(20).mean().iloc[-1])
        ma50 = float(s.rolling(50).mean().iloc[-1])
        ma200 = float(s.rolling(200).mean().iloc[-1])
        ret_1m = float(s.pct_change(21).iloc[-1])
        ret_3m = float(s.pct_change(63).iloc[-1])
        ret_6m = float(s.pct_change(126).iloc[-1])
        vol = float(s.pct_change().rolling(63).std().iloc[-1] * np.sqrt(252))
        drawdown = float(last / s.cummax().iloc[-1] - 1)

        trend_points = 0.0
        trend_points += 35 if last > ma200 else 0
        trend_points += 25 if ma50 > ma200 else 0
        trend_points += 20 if last > ma50 else 0
        trend_points += 20 if ma20 > ma50 else 0

        momentum_points = _bounded(50 + ret_1m * 180 + ret_3m * 110 + ret_6m * 55)
        volatility_points = _bounded(100 - vol * 140)
        drawdown_points = _bounded(100 + drawdown * 250)
        score = (
            trend_points * 0.40
            + momentum_points * 0.35
            + volatility_points * 0.15
            + drawdown_points * 0.10
        )
        confidence = _bounded(55 + abs(score - 50) * 0.75)
        rows.append(
            {
                "symbol": symbol,
                "price": round(last, 2),
                "score": round(score, 1),
                "confidence": round(confidence, 1),
                "signal": _signal(score),
                "return_1m_pct": round(ret_1m * 100, 2),
                "return_3m_pct": round(ret_3m * 100, 2),
                "return_6m_pct": round(ret_6m * 100, 2),
                "volatility_pct": round(vol * 100, 2),
                "drawdown_pct": round(drawdown * 100, 2),
                "above_ma200": bool(last > ma200),
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["score", "confidence"], ascending=False).reset_index(drop=True)
