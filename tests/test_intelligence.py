from elan_ai_invest.intelligence.engine import IntelligenceEngine
from elan_ai_invest.intelligence.models import (
    TrendResult,
    MomentumResult,
    RiskResult,
    MarketResult,
)


def test_intelligence():

    engine = IntelligenceEngine()

    result = engine.analyze(
        TrendResult(92, 90),
        MomentumResult(88, 85),
        RiskResult(75, 82),
        MarketResult("RISK_ON", 88),
    )

    assert result.action.value == "BUY"