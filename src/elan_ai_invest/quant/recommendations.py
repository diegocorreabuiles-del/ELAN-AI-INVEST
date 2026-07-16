from __future__ import annotations

import pandas as pd


def decision_from_score(score: float, regime: str = "Mixto") -> str:
    if regime == "Defensivo" and score < 80:
        return "ESPERAR"
    if score >= 82:
        return "COMPRAR"
    if score >= 68:
        return "VIGILAR"
    if score >= 50:
        return "NEUTRAL"
    return "EVITAR"


def explain_row(row: pd.Series) -> str:
    reasons: list[str] = []
    if float(row.get("trend_factor", 0)) >= 75:
        reasons.append("tendencia primaria sólida")
    if float(row.get("relative_strength_factor", 0)) >= 65:
        reasons.append("fuerza relativa superior al benchmark")
    if float(row.get("risk_adjusted_factor", 0)) >= 60:
        reasons.append("rentabilidad ajustada por riesgo favorable")
    if float(row.get("trend_quality_factor", 0)) >= 55:
        reasons.append("movimiento de precio consistente")
    if float(row.get("volatility_pct", 100)) <= 25:
        reasons.append("volatilidad controlada")
    if not reasons:
        reasons.append("la señal todavía no reúne suficientes confirmaciones")
    return "; ".join(reasons).capitalize() + "."
