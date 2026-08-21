from datetime import UTC, datetime

import pytest

from elan_ai_invest.analysis import (
    ASSET_SCORE_WEIGHTS,
    AssetProfile,
    AssetType,
    DataConfidence,
    DecisionAction,
    DecisionPolicy,
    FundamentalMetrics,
    RiskMetrics,
    StablecoinMetrics,
    TechnicalMetrics,
    calculate_data_confidence,
    calculate_score_breakdown,
    decide,
)
from elan_ai_invest.providers.base import MarketDataAssetQuality, MarketDataQualityStatus


def profile(asset_type: AssetType) -> AssetProfile:
    return AssetProfile(symbol="TEST", name="Test", asset_type=asset_type)


def confidence(score: float = 90.0) -> DataConfidence:
    return DataConfidence(score=score)


def quality(
    status: MarketDataQualityStatus = MarketDataQualityStatus.HEALTHY,
    *,
    coverage: float = 1.0,
    age_days: int | None = 0,
) -> MarketDataAssetQuality:
    now = datetime.now(UTC)
    return MarketDataAssetQuality(
        symbol="TEST",
        status=status,
        source="test",
        observations=100,
        expected_sessions=100,
        missing_sessions=round((1 - coverage) * 100),
        coverage_ratio=coverage,
        first_observation=now,
        last_observation=now,
        age_days=age_days,
    )


def test_all_asset_weight_sets_are_normalized() -> None:
    assert set(ASSET_SCORE_WEIGHTS) == set(AssetType)
    for weights in ASSET_SCORE_WEIGHTS.values():
        assert sum(weights.values()) == pytest.approx(1.0)
        assert all(weight > 0 for weight in weights.values())


def test_missing_components_redistribute_weight_proportionally() -> None:
    result = calculate_score_breakdown(
        profile(AssetType.EQUITY),
        technical=TechnicalMetrics(score=80),
        risk=RiskMetrics(score=60),
    )

    assert result.conviction == pytest.approx((80 * 0.25 + 60 * 0.20) / 0.45)
    assert result.fundamental is None
    assert result.available() == {"technical": 80, "risk": 60}


def test_no_components_remain_unavailable_instead_of_zero() -> None:
    result = calculate_score_breakdown(profile(AssetType.EQUITY))

    assert result.conviction is None
    assert result.available() == {}


def test_crypto_ignores_corporate_fundamentals() -> None:
    result = calculate_score_breakdown(
        profile(AssetType.CRYPTO),
        technical=TechnicalMetrics(score=70),
        fundamental=FundamentalMetrics(score=100),
        risk=RiskMetrics(score=50),
    )

    assert result.fundamental is None
    assert result.conviction == pytest.approx((70 * 0.35 + 50 * 0.30) / 0.65)


def test_stablecoin_uses_stability_components_only() -> None:
    result = calculate_score_breakdown(
        profile(AssetType.STABLECOIN),
        technical=TechnicalMetrics(score=100),
        stablecoin=StablecoinMetrics(
            peg_health_score=90,
            liquidity_health_score=80,
            issuer_risk_score=70,
            adoption_trend_score=60,
        ),
    )

    assert result.technical is None
    assert result.conviction == pytest.approx(78.0)
    assert set(result.available()) == {"peg_health", "liquidity", "issuer_risk", "adoption"}


def test_healthy_data_produces_high_observable_confidence() -> None:
    result = calculate_data_confidence(
        quality(),
        available_fields=10,
        expected_fields=10,
        provider_score=90,
    )

    assert result.score == pytest.approx(99.0)
    assert result.warnings == ()


def test_unavailable_provider_status_caps_confidence_at_zero() -> None:
    result = calculate_data_confidence(
        quality(MarketDataQualityStatus.UNAVAILABLE),
        available_fields=10,
        expected_fields=10,
        provider_score=100,
    )

    assert result.score == 0
    assert any("disponibles" in warning for warning in result.warnings)


def test_stale_and_error_signals_reduce_confidence_and_add_warnings() -> None:
    result = calculate_data_confidence(
        quality(MarketDataQualityStatus.STALE, coverage=0.75, age_days=5),
        available_fields=4,
        expected_fields=10,
        provider_score=80,
        error_count=2,
    )

    assert result.score < 50
    assert len(result.warnings) >= 4


def test_absent_quality_evidence_is_zero_confidence() -> None:
    result = calculate_data_confidence(None)

    assert result.score == 0
    assert result.coverage_score is None
    assert result.warnings


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (80, DecisionAction.BUY),
        (79.999, DecisionAction.ACCUMULATE),
        (65, DecisionAction.ACCUMULATE),
        (45, DecisionAction.WAIT),
        (30, DecisionAction.REDUCE),
        (29.999, DecisionAction.SELL),
    ],
)
def test_decision_threshold_boundaries(score: float, expected: DecisionAction) -> None:
    assert (
        decide(
            score,
            asset_type=AssetType.EQUITY,
            data_confidence=confidence(),
        ).action
        is expected
    )


def test_low_data_confidence_blocks_both_strong_buy_and_sell() -> None:
    buy = decide(90, asset_type=AssetType.EQUITY, data_confidence=confidence(39))
    sell = decide(20, asset_type=AssetType.EQUITY, data_confidence=confidence(39))

    assert buy.action is DecisionAction.WAIT
    assert sell.action is DecisionAction.WAIT
    assert buy.limited_by_data_quality
    assert sell.limited_by_data_quality


def test_moderate_confidence_caps_buy_at_accumulate() -> None:
    result = decide(90, asset_type=AssetType.EQUITY, data_confidence=confidence(69))

    assert result.base_action is DecisionAction.BUY
    assert result.action is DecisionAction.ACCUMULATE


@pytest.mark.parametrize("gate", [{"risk_score": 29}, {"trend_score": 34}])
def test_risk_and_trend_gates_block_bullish_action(gate: dict[str, float]) -> None:
    result = decide(
        90,
        asset_type=AssetType.EQUITY,
        data_confidence=confidence(),
        **gate,
    )

    assert result.action is DecisionAction.WAIT
    assert result.reasons


def test_context_and_speculative_profiles_limit_buy() -> None:
    defensive = decide(
        90,
        asset_type=AssetType.EQUITY,
        data_confidence=confidence(),
        market_regime="risk-off",
    )
    meme = decide(90, asset_type=AssetType.MEME_COIN, data_confidence=confidence())
    unknown = decide(90, asset_type=AssetType.UNKNOWN, data_confidence=confidence())

    assert defensive.action is DecisionAction.ACCUMULATE
    assert meme.action is DecisionAction.ACCUMULATE
    assert unknown.action is DecisionAction.WAIT


def test_stablecoin_never_uses_directional_price_action() -> None:
    result = decide(95, asset_type=AssetType.STABLECOIN, data_confidence=confidence())

    assert result.base_action is DecisionAction.BUY
    assert result.action is DecisionAction.WAIT


def test_missing_conviction_returns_not_available() -> None:
    result = decide(None, asset_type=AssetType.EQUITY, data_confidence=confidence())

    assert result.action is DecisionAction.NOT_AVAILABLE
    assert result.limited_by_data_quality


def test_invalid_policy_order_is_rejected() -> None:
    with pytest.raises(ValueError, match="estrictamente ordenados"):
        DecisionPolicy(buy_threshold=65, accumulate_threshold=80)
