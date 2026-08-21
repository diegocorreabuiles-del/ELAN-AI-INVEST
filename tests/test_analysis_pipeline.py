from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from elan_ai_invest.analysis import (
    AssetProfile,
    AssetType,
    DecisionAction,
    build_asset_analysis,
)
from elan_ai_invest.providers.base import (
    MarketDataAssetQuality,
    MarketDataQualityStatus,
)


def _history() -> pd.DataFrame:
    index = pd.bdate_range("2025-01-01", periods=260)
    x = np.arange(len(index), dtype=float)
    close = pd.Series(100 + x * 0.08 + np.sin(x / 5) * 2, index=index)
    return pd.DataFrame(
        {
            "Open": close - 0.2,
            "High": close + 1.2,
            "Low": close - 1.2,
            "Close": close,
            "Volume": 1_000_000 + (np.sin(x / 7) + 1) * 100_000,
        },
        index=index,
    )


def _quality(symbol: str) -> MarketDataAssetQuality:
    return MarketDataAssetQuality(
        symbol=symbol,
        status=MarketDataQualityStatus.HEALTHY,
        source="provider",
        observations=260,
        expected_sessions=260,
        missing_sessions=0,
        coverage_ratio=1.0,
        first_observation=datetime(2025, 1, 1, tzinfo=UTC),
        last_observation=datetime(2025, 12, 31, tzinfo=UTC),
        age_days=1,
    )


def test_pipeline_assembles_observed_metrics_scores_and_decision() -> None:
    profile = AssetProfile(symbol="AAPL", name="Apple", asset_type=AssetType.EQUITY)
    history = _history()

    result = build_asset_analysis(
        profile,
        history,
        quality=_quality("AAPL"),
        benchmark_history=history["Close"] * 1.01,
        market_regime="Alcista",
    )

    assert result.market.price == history["Close"].iloc[-1]
    assert result.market.change_1d_pct is not None
    assert result.technical is not None and result.technical.score is not None
    assert result.risk is not None and result.risk.score is not None
    assert result.scores.conviction is not None
    assert result.scores.fundamental is None
    assert result.data_confidence is not None
    assert result.data_confidence.score == 100.0
    assert result.decision is not DecisionAction.NOT_AVAILABLE
    assert result.trade_plan is not None
    assert result.positives or result.negatives


def test_pipeline_data_errors_reduce_confidence_without_inventing_fields() -> None:
    profile = AssetProfile(symbol="AAPL", name="Apple", asset_type=AssetType.EQUITY)

    clean = build_asset_analysis(profile, _history(), quality=_quality("AAPL"))
    degraded = build_asset_analysis(
        profile,
        _history(),
        quality=_quality("AAPL"),
        error_count=2,
    )

    assert clean.data_confidence is not None
    assert degraded.data_confidence is not None
    assert degraded.data_confidence.score == clean.data_confidence.score - 20
    assert "Se registraron 2 errores de datos." in degraded.data_confidence.warnings


def test_pipeline_stablecoin_uses_peg_model_and_skips_directional_plan() -> None:
    profile = AssetProfile(
        symbol="USDC-USD",
        name="USD Coin",
        asset_type=AssetType.STABLECOIN,
    )
    history = _history()
    history["Open"] = 1.0
    history["High"] = 1.002
    history["Low"] = 0.998
    history["Close"] = 1.0

    result = build_asset_analysis(profile, history, quality=_quality("USDC-USD"))

    assert result.stablecoin is not None
    assert result.stablecoin.peg_health_score == 100.0
    assert result.scores.conviction == 100.0
    assert result.scores.technical is None
    assert result.decision is DecisionAction.WAIT
    assert result.trade_plan is not None
    assert not result.trade_plan.sufficient_data
    assert "stablecoin" in result.trade_plan.rationale[0].casefold()


def test_pipeline_populates_only_the_matching_crypto_specific_model() -> None:
    crypto_profile = AssetProfile(
        symbol="ETH-USD",
        name="Ethereum",
        asset_type=AssetType.CRYPTO,
    )
    meme_profile = AssetProfile(
        symbol="DOGE-USD",
        name="Dogecoin",
        asset_type=AssetType.MEME_COIN,
    )
    history = _history()

    crypto = build_asset_analysis(
        crypto_profile,
        history,
        quality=_quality("ETH-USD"),
        benchmark_history=history["Close"] * 0.95,
    )
    meme = build_asset_analysis(
        meme_profile,
        history,
        quality=_quality("DOGE-USD"),
    )

    assert crypto.crypto is not None
    assert crypto.meme_coin is None
    assert crypto.stablecoin is None
    assert crypto.scores.fundamental is None
    assert meme.crypto is None
    assert meme.meme_coin is not None
    assert meme.stablecoin is None
    assert meme.meme_coin.social_momentum_score is None
    assert meme.decision is not DecisionAction.BUY
