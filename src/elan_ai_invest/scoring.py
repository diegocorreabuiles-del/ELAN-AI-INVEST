from __future__ import annotations

import numpy as np
import pandas as pd

from elan_ai_invest.core.config import ScoringConfig
from elan_ai_invest.quant import calculate_factor_table, decision_from_score, explain_row


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


def score_assets(
    prices: pd.DataFrame,
    config: ScoringConfig | None = None,
    benchmark: str = "SPY",
) -> pd.DataFrame:
    config = config or ScoringConfig()
    factors = calculate_factor_table(prices, benchmark=benchmark)
    factor_map = factors.set_index("symbol").to_dict("index") if not factors.empty else {}

    rows: list[dict[str, float | str | bool]] = []
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
        base_score = (
            trend_points * config.trend_weight
            + momentum_points * config.momentum_weight
            + volatility_points * config.volatility_weight
            + drawdown_points * config.drawdown_weight
        )

        factor_data = factor_map.get(symbol, {})
        professional_overlay = (
            float(factor_data.get("relative_strength_factor", 50)) * 0.45
            + float(factor_data.get("risk_adjusted_factor", 50)) * 0.30
            + float(factor_data.get("trend_quality_factor", 50)) * 0.25
        )
        score = _bounded(base_score * 0.75 + professional_overlay * 0.25)
        confidence = _bounded(
            50
            + abs(score - 50) * 0.55
            + abs(float(factor_data.get("trend_factor", 50)) - 50) * 0.15
        )

        row: dict[str, float | str | bool] = {
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
        row.update(factor_data)
        row["decision"] = decision_from_score(score)
        row["explanation"] = explain_row(pd.Series(row))
        rows.append(row)

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["score", "confidence"], ascending=False).reset_index(drop=True)
