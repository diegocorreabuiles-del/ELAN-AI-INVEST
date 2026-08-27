from .confidence import calculate_confidence
from .decision import make_decision
from .explain import build_explanation
from .models import Decision, MarketResult, MomentumResult, RiskResult, TrendResult


class IntelligenceEngine:
    def analyze(
        self,
        trend: TrendResult,
        momentum: MomentumResult,
        risk: RiskResult,
        market: MarketResult,
    ) -> Decision:
        decision = make_decision(trend, momentum, risk, market)
        decision.confidence = calculate_confidence(trend, momentum, risk, market)
        decision.explanation = build_explanation(decision, trend, momentum, risk, market)
        return decision
