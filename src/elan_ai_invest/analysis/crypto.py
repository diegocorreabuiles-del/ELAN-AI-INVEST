from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .models import (
    CryptoMetrics,
    DepegRisk,
    MarketMetrics,
    MemeCoinMetrics,
    StablecoinMetrics,
    TechnicalMetrics,
)
from .technical import calculate_market_metrics, calculate_technical_metrics, clean_ohlcv

_SESSIONS_30D = 21
_VOLUME_WINDOW = 20


def _finite(value: float | np.floating | None) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _bounded(value: float) -> float:
    return float(np.clip(value, 0.0, 100.0))


def _close_series(data: pd.DataFrame | pd.Series | None) -> pd.Series:
    if data is None:
        return pd.Series(dtype=float)
    if isinstance(data, pd.DataFrame):
        if "Close" not in data:
            return pd.Series(dtype=float)
        values = data["Close"]
    else:
        values = data
    clean = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan)
    clean = clean.sort_index()
    clean = clean.loc[~clean.index.duplicated(keep="last")]
    return clean.where(clean > 0).dropna()


def _relative_strength_30d(
    history: pd.DataFrame,
    benchmark_history: pd.DataFrame | pd.Series | None,
) -> float | None:
    asset = _close_series(history).rename("asset")
    benchmark = _close_series(benchmark_history).rename("benchmark")
    aligned = pd.concat((asset, benchmark), axis=1).dropna()
    if len(aligned) <= _SESSIONS_30D:
        return None
    window = aligned.tail(_SESSIONS_30D + 1)
    asset_return = float(window["asset"].iloc[-1] / window["asset"].iloc[0] - 1.0)
    benchmark_return = float(window["benchmark"].iloc[-1] / window["benchmark"].iloc[0] - 1.0)
    return _finite((asset_return - benchmark_return) * 100.0)


def _volume_change_20d(history: pd.DataFrame) -> float | None:
    clean = clean_ohlcv(history)
    if "Volume" not in clean or len(clean) < _VOLUME_WINDOW * 2:
        return None
    volume = pd.to_numeric(clean["Volume"], errors="coerce")
    recent = volume.tail(_VOLUME_WINDOW)
    previous = volume.iloc[-_VOLUME_WINDOW * 2 : -_VOLUME_WINDOW]
    if (
        recent.isna().any()
        or previous.isna().any()
        or not recent.gt(0).all()
        or not previous.gt(0).all()
    ):
        return None
    previous_average = float(previous.mean())
    if previous_average <= 0:
        return None
    return _finite((float(recent.mean()) / previous_average - 1.0) * 100.0)


def calculate_crypto_metrics(
    history: pd.DataFrame,
    benchmark_history: pd.DataFrame | pd.Series | None = None,
    *,
    market: MarketMetrics | None = None,
) -> CryptoMetrics:
    """Derive only Yahoo/OHLCV-backed crypto market metrics.

    Derivatives, exchange flows and on-chain/network fields remain unavailable
    until an explicit provider supplies them.
    """

    observed_market = market or calculate_market_metrics(history)
    return CryptoMetrics(
        btc_relative_strength_30d_pct=_relative_strength_30d(history, benchmark_history),
        volume_change_20d_pct=_volume_change_20d(history),
        average_dollar_volume=observed_market.average_dollar_volume,
    )


def calculate_meme_coin_metrics(
    history: pd.DataFrame,
    *,
    market: MarketMetrics | None = None,
    technical: TechnicalMetrics | None = None,
) -> MemeCoinMetrics:
    """Expose speculative-market proxies without inventing DEX, holder or social data."""

    observed_market = market or calculate_market_metrics(history)
    observed_technical = technical or calculate_technical_metrics(history)
    return MemeCoinMetrics(
        momentum_score=observed_technical.momentum_score,
        volume_score=observed_technical.volume_score,
        rvol_20=observed_technical.rvol_20,
        volume_change_20d_pct=_volume_change_20d(history),
        average_dollar_volume=observed_market.average_dollar_volume,
    )


def _depeg_risk(current_deviation: float, maximum_deviation: float) -> DepegRisk:
    current = abs(current_deviation)
    maximum = abs(maximum_deviation)
    if current >= 3.0 or maximum >= 5.0:
        return DepegRisk.CRITICAL
    if current >= 1.0 or maximum >= 2.0:
        return DepegRisk.HIGH
    if current >= 0.25 or maximum >= 0.5:
        return DepegRisk.MODERATE
    return DepegRisk.LOW


def calculate_stablecoin_metrics(
    history: pd.DataFrame,
    *,
    market: MarketMetrics | None = None,
) -> StablecoinMetrics:
    """Measure the observed USD peg; never infer reserves, issuer risk or supply."""

    clean = clean_ohlcv(history)
    close = _close_series(clean)
    if close.empty:
        return StablecoinMetrics()
    current_deviation = (float(close.iloc[-1]) - 1.0) * 100.0
    recent_deviations = (close.tail(30) - 1.0).abs() * 100.0
    maximum_deviation = float(recent_deviations.max())
    current_health = _bounded(100.0 - abs(current_deviation) * 100.0)
    observed_health = _bounded(100.0 - maximum_deviation * 50.0)
    peg_health = current_health * 0.65 + observed_health * 0.35
    observed_market = market or calculate_market_metrics(history)
    return StablecoinMetrics(
        peg_health_score=peg_health,
        peg_deviation_pct=current_deviation,
        max_peg_deviation_30d_pct=maximum_deviation,
        depeg_risk=_depeg_risk(current_deviation, maximum_deviation),
        volume_change_20d_pct=_volume_change_20d(history),
        average_dollar_volume=observed_market.average_dollar_volume,
    )
