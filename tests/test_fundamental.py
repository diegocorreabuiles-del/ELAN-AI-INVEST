from elan_ai_invest.fundamental import FundamentalSnapshot, analyze_fundamentals


def test_fundamental_scoring_rewards_quality_and_growth():
    snapshot = FundamentalSnapshot(
        symbol="TEST",
        company_name="Test Company",
        forward_pe=18.0,
        trailing_pe=20.0,
        peg_ratio=1.2,
        enterprise_to_ebitda=12.0,
        return_on_equity=0.25,
        return_on_assets=0.12,
        profit_margin=0.20,
        operating_margin=0.24,
        revenue_growth=0.15,
        earnings_growth=0.20,
        debt_to_equity=40.0,
        current_ratio=1.8,
        free_cash_flow=1_000_000,
        operating_cash_flow=1_300_000,
    )
    result = analyze_fundamentals(snapshot)
    assert result.score >= 65
    assert result.confidence > 70
    assert result.decision in {"CALIDAD ALTA", "FAVORABLE"}


def test_fundamental_scoring_handles_missing_data():
    result = analyze_fundamentals(FundamentalSnapshot(symbol="X", company_name="X"))
    assert 0 <= result.score <= 100
    assert result.confidence < 60
