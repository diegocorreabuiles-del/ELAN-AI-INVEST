from __future__ import annotations

from pathlib import Path

import pytest

from elan_ai_invest.analysis import (
    AssetAnalysis,
    AssetProfile,
    AssetType,
    CryptoMetrics,
    FundamentalMetrics,
    MemeCoinMetrics,
    ScoreBreakdown,
    StablecoinMetrics,
    classify_asset,
)
from elan_ai_invest.instruments import load_instrument_catalog


@pytest.fixture(scope="module")
def catalog():
    path = Path(__file__).parents[1] / "config" / "instruments.csv"
    return load_instrument_catalog(path)


@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("AAPL", AssetType.EQUITY),
        ("SPY", AssetType.ETF),
        ("BTC-USD", AssetType.CRYPTO),
        ("DOGE-USD", AssetType.MEME_COIN),
        ("USDC-USD", AssetType.STABLECOIN),
        ("RLUSD-USD", AssetType.STABLECOIN),
        ("WIF-USD", AssetType.MEME_COIN),
        ("EURUSD=X", AssetType.FOREX),
    ],
)
def test_catalog_classification_covers_supported_asset_models(catalog, symbol, expected) -> None:
    profile = classify_asset(symbol, catalog)

    assert profile.asset_type is expected
    assert profile.classification_source == "catalog"
    assert profile.classification_confidence == 100.0


def test_us_equity_benchmark_depends_on_exchange(catalog) -> None:
    assert classify_asset("AAPL", catalog).benchmark == "QQQ"
    assert classify_asset("EC", catalog).benchmark == "SPY"


def test_manual_symbol_inference_is_conservative() -> None:
    assert classify_asset("1810.HK").asset_type is AssetType.EQUITY
    assert classify_asset("SOMECOIN-USD").asset_type is AssetType.CRYPTO
    assert classify_asset("USDE29470-USD").asset_type is AssetType.STABLECOIN
    assert classify_asset("TRUMP35336-USD").asset_type is AssetType.MEME_COIN
    assert classify_asset("FX_EUR_GBP").asset_type is AssetType.FOREX
    unknown = classify_asset("UNLISTED")
    assert unknown.asset_type is AssetType.UNKNOWN
    assert unknown.classification_confidence == 0.0


def test_missing_scores_remain_unavailable_instead_of_becoming_zero() -> None:
    scores = ScoreBreakdown(technical=72.0, risk=61.0)

    assert scores.fundamental is None
    assert scores.available() == {"technical": 72.0, "risk": 61.0}


def test_scores_reject_nan_infinity_and_out_of_range_values() -> None:
    for invalid in (float("nan"), float("inf"), -0.1, 100.1):
        with pytest.raises(ValueError):
            ScoreBreakdown(technical=invalid)


@pytest.mark.parametrize(
    "asset_type",
    [AssetType.CRYPTO, AssetType.MEME_COIN, AssetType.STABLECOIN, AssetType.ETF],
)
def test_corporate_metrics_cannot_be_attached_to_non_equities(asset_type) -> None:
    profile = AssetProfile(symbol="X", name="X", asset_type=asset_type)

    with pytest.raises(ValueError, match="solo son válidas para acciones"):
        AssetAnalysis(profile=profile, fundamental=FundamentalMetrics(score=70.0))


def test_stablecoin_metrics_are_restricted_to_stablecoins() -> None:
    crypto = AssetProfile(symbol="BTC-USD", name="Bitcoin", asset_type=AssetType.CRYPTO)
    with pytest.raises(ValueError, match="solo son válidas para stablecoins"):
        AssetAnalysis(crypto, stablecoin=StablecoinMetrics(peg_health_score=99.0))

    stablecoin = AssetProfile(symbol="USDC-USD", name="USDC", asset_type=AssetType.STABLECOIN)
    analysis = AssetAnalysis(
        stablecoin,
        stablecoin=StablecoinMetrics(peg_health_score=99.0),
    )
    assert analysis.stablecoin is not None


def test_crypto_specific_models_cannot_cross_asset_types() -> None:
    crypto = AssetProfile(symbol="BTC-USD", name="Bitcoin", asset_type=AssetType.CRYPTO)
    meme = AssetProfile(symbol="DOGE-USD", name="Dogecoin", asset_type=AssetType.MEME_COIN)

    with pytest.raises(ValueError, match="solo son válidas para criptomonedas"):
        AssetAnalysis(meme, crypto=CryptoMetrics())
    with pytest.raises(ValueError, match="solo son válidas para meme coins"):
        AssetAnalysis(crypto, meme_coin=MemeCoinMetrics())

    assert AssetAnalysis(crypto, crypto=CryptoMetrics()).crypto is not None
    assert AssetAnalysis(meme, meme_coin=MemeCoinMetrics()).meme_coin is not None
