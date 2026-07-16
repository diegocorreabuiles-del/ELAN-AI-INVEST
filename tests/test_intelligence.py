from elan_ai_invest.intelligence import (
    IntelligenceEngine,
    MarketResult,
    MomentumResult,
    RiskResult,
    TrendResult,
)


def test_intelligence_buy():
    result = IntelligenceEngine().analyze(
        TrendResult(92, 90), MomentumResult(88, 85), RiskResult(75, 82), MarketResult("RISK_ON", 88)
    )
    assert result.action.value == "BUY"
    assert result.explanation
