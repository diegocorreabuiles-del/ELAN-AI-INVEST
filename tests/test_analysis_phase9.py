from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from elan_ai_invest.analysis import (
    AssetProfile,
    AssetType,
    DecisionAction,
    DepegRisk,
    build_asset_analysis,
    calculate_stablecoin_metrics,
)
from elan_ai_invest.providers.base import MarketDataAssetQuality, MarketDataQualityStatus


def _history(
    close: np.ndarray,
    *,
    volume: np.ndarray | None = None,
    spread_pct: float = 0.01,
) -> pd.DataFrame:
    index = pd.bdate_range("2025-01-01", periods=len(close))
    observed_volume = volume if volume is not None else np.full(len(close), 1_000_000.0)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * (1.0 + spread_pct),
            "Low": close * (1.0 - spread_pct),
            "Close": close,
            "Volume": observed_volume,
        },
        index=index,
    )


def _quality(symbol: str, observations: int = 260) -> MarketDataAssetQuality:
    now = datetime.now(UTC)
    return MarketDataAssetQuality(
        symbol=symbol,
        status=MarketDataQualityStatus.HEALTHY,
        source="phase9-fixture",
        observations=observations,
        expected_sessions=observations,
        missing_sessions=0,
        coverage_ratio=1.0,
        first_observation=now,
        last_observation=now,
        age_days=0,
    )


def _complete_history() -> pd.DataFrame:
    x = np.arange(260, dtype=float)
    close = 100.0 + x * 0.06 + np.sin(x / 6.0) * 2.0
    volume = 1_000_000.0 + (np.cos(x / 8.0) + 1.0) * 150_000.0
    return _history(close, volume=volume)


def _assert_score_invariants(analysis) -> None:
    for value in analysis.scores.available().values():
        assert math.isfinite(value)
        assert 0.0 <= value <= 100.0
    if analysis.scores.conviction is not None:
        assert math.isfinite(analysis.scores.conviction)
        assert 0.0 <= analysis.scores.conviction <= 100.0
    for metrics in (analysis.technical, analysis.risk):
        assert metrics is not None
        if metrics.score is not None:
            assert math.isfinite(metrics.score)
            assert 0.0 <= metrics.score <= 100.0


@pytest.mark.parametrize("asset_type", list(AssetType))
def test_pipeline_preserves_invariants_for_every_asset_type(asset_type: AssetType) -> None:
    symbol = f"PHASE9-{asset_type.value.upper()}"
    history = _complete_history()
    if asset_type is AssetType.STABLECOIN:
        history = _history(np.ones(260), spread_pct=0.002)

    result = build_asset_analysis(
        AssetProfile(symbol=symbol, name=symbol, asset_type=asset_type),
        history,
        quality=_quality(symbol),
        benchmark_history=_complete_history()["Close"] * 0.97,
    )

    _assert_score_invariants(result)
    assert result.scores.fundamental is None
    assert (result.crypto is not None) is (asset_type is AssetType.CRYPTO)
    assert (result.meme_coin is not None) is (asset_type is AssetType.MEME_COIN)
    assert (result.stablecoin is not None) is (asset_type is AssetType.STABLECOIN)
    if asset_type is AssetType.STABLECOIN:
        assert result.decision is DecisionAction.WAIT
        assert result.trade_plan is not None and not result.trade_plan.sufficient_data
    elif asset_type is AssetType.MEME_COIN:
        assert result.decision is not DecisionAction.BUY
    elif asset_type is AssetType.UNKNOWN:
        assert result.decision not in {DecisionAction.BUY, DecisionAction.ACCUMULATE}


def test_short_history_fails_closed_without_partial_directional_decision() -> None:
    history = _history(np.linspace(100.0, 101.0, 10))
    result = build_asset_analysis(
        AssetProfile(symbol="SHORT", name="Short", asset_type=AssetType.EQUITY),
        history,
        quality=_quality("SHORT", observations=10),
    )

    assert result.technical is not None and result.technical.score is None
    assert result.risk is not None and result.risk.score is None
    assert result.scores.conviction is None
    assert result.decision is DecisionAction.NOT_AVAILABLE
    assert result.decision_limited_by_data_quality
    assert result.trade_plan is not None and not result.trade_plan.sufficient_data


def test_nonfinite_duplicate_rows_are_contained_without_fabricated_crypto_data() -> None:
    history = _complete_history()
    history.loc[history.index[40], ["Open", "High", "Low", "Close"]] = np.nan
    history.loc[history.index[80], ["Open", "High", "Low", "Close"]] = np.inf
    history.loc[history.index[-1], "Volume"] = 0.0
    duplicate = history.iloc[[-2]].copy()
    duplicate.index = pd.DatetimeIndex([history.index[-3]])
    history = pd.concat((history, duplicate)).sort_index()

    result = build_asset_analysis(
        AssetProfile(symbol="ETH-USD", name="Ethereum", asset_type=AssetType.CRYPTO),
        history,
        quality=_quality("ETH-USD"),
        benchmark_history=_complete_history()["Close"],
    )

    _assert_score_invariants(result)
    assert result.market.price is not None and math.isfinite(result.market.price)
    assert result.crypto is not None
    assert result.crypto.volume_change_20d_pct is None
    assert result.crypto.funding_rate_pct is None
    assert result.crypto.open_interest is None


def test_extreme_positive_scale_keeps_all_published_scores_finite_and_bounded() -> None:
    history = _history(np.geomspace(1e-6, 1e12, 260), spread_pct=0.02)
    result = build_asset_analysis(
        AssetProfile(symbol="SCALE", name="Scale", asset_type=AssetType.COMMODITY),
        history,
        quality=_quality("SCALE"),
    )

    _assert_score_invariants(result)
    assert result.market.price == pytest.approx(1e12)
    assert result.market.average_dollar_volume is not None
    assert math.isfinite(result.market.average_dollar_volume)


def test_extreme_volatility_blocks_a_bullish_crypto_decision() -> None:
    returns = np.resize(np.array([0.35, -0.26]), 259)
    close = 100.0 * np.concatenate(([1.0], np.cumprod(1.0 + returns)))
    history = _history(close, spread_pct=0.05)
    result = build_asset_analysis(
        AssetProfile(symbol="VOL-USD", name="Volatile", asset_type=AssetType.CRYPTO),
        history,
        quality=_quality("VOL-USD"),
        benchmark_history=_complete_history()["Close"],
    )

    _assert_score_invariants(result)
    assert result.risk is not None and result.risk.score is not None
    assert result.risk.score < 45.0
    assert result.decision not in {DecisionAction.BUY, DecisionAction.ACCUMULATE}


@pytest.mark.parametrize(
    ("last_price", "expected"),
    [
        (0.997, DepegRisk.MODERATE),
        (0.989, DepegRisk.HIGH),
        (0.969, DepegRisk.CRITICAL),
    ],
)
def test_depeg_thresholds_escalate_conservatively(
    last_price: float,
    expected: DepegRisk,
) -> None:
    close = np.ones(60)
    close[-1] = last_price

    result = calculate_stablecoin_metrics(_history(close, spread_pct=0.002))

    assert result.depeg_risk is expected
    assert result.peg_health_score is not None
    assert 0.0 <= result.peg_health_score <= 100.0


def test_transient_depeg_remains_visible_after_price_recovers() -> None:
    close = np.ones(60)
    close[-10] = 0.94
    history = _history(close, spread_pct=0.002)
    result = build_asset_analysis(
        AssetProfile(
            symbol="USDC-USD",
            name="USD Coin",
            asset_type=AssetType.STABLECOIN,
        ),
        history,
        quality=_quality("USDC-USD", observations=60),
    )

    assert result.stablecoin is not None
    assert result.stablecoin.depeg_risk is DepegRisk.CRITICAL
    assert result.stablecoin.max_peg_deviation_30d_pct == pytest.approx(6.0)
    assert result.decision is DecisionAction.WAIT
    assert result.trade_plan is not None and not result.trade_plan.sufficient_data
    assert any("depeg crítico" in reason.casefold() for reason in result.negatives)


def test_dashboard_package_exports_decision_terminal_contract() -> None:
    from elan_ai_invest.dashboard import load_decision_analysis, render_decision_terminal

    assert load_decision_analysis.__module__.endswith("decision_terminal")
    assert render_decision_terminal.__module__.endswith("decision_terminal")
