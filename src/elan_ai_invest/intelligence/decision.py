from .models import Decision, DecisionType, MarketResult, MomentumResult, RiskResult, TrendResult


def make_decision(
    trend: TrendResult,
    momentum: MomentumResult,
    risk: RiskResult,
    market: MarketResult,
) -> Decision:
    score = (
        trend.score * 0.35 + momentum.score * 0.35 + risk.score * 0.20 + market.confidence * 0.10
    )
    if market.regime == "RISK_OFF":
        action = DecisionType.WAIT if score >= 45 else DecisionType.REDUCE
    elif score >= 82:
        action = DecisionType.BUY
    elif score >= 68:
        action = DecisionType.HOLD
    elif score >= 48:
        action = DecisionType.WAIT
    elif score >= 30:
        action = DecisionType.REDUCE
    else:
        action = DecisionType.SELL
    return Decision(action=action, score=round(score, 1), confidence=0.0, explanation="")
