from .models import Decision, MarketResult, MomentumResult, RiskResult, TrendResult


def build_explanation(
    decision: Decision,
    trend: TrendResult,
    momentum: MomentumResult,
    risk: RiskResult,
    market: MarketResult,
) -> str:
    reasons: list[str] = []
    reasons.append("tendencia sólida" if trend.score >= 70 else "tendencia débil")
    reasons.append("momentum favorable" if momentum.score >= 65 else "momentum limitado")
    reasons.append("riesgo controlado" if risk.score >= 60 else "riesgo elevado")
    reasons.append(f"entorno {market.regime.lower()}")
    return f"{decision.action.value}: " + ", ".join(reasons) + "."
