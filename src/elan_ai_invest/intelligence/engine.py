from .confidence import calculate_confidence
from .decision import make_decision
from .explain import build_explanation
from .models import (
    MarketResult,
    MomentumResult,
    RiskResult,
    TrendResult,
)


class IntelligenceEngine:

    def analyze(
        self,
        trend: TrendResult,
        momentum: MomentumResult,
        risk: RiskResult,
        market: MarketResult,
    ):

        decision = make_decision(
            trend,
            momentum,
            risk,
            market,
        )

        decision.confidence = calculate_confidence(
            trend,
            momentum,
            risk,
            market,
        )

        decision.explanation = build_explanation(decision)

        return decision