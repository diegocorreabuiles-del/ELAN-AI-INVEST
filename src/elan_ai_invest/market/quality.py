from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime

import pandas as pd

from elan_ai_invest.providers.base import (
    MarketDataAssetQuality,
    MarketDataQualityReport,
    MarketDataQualityStatus,
)

DEFAULT_MAX_STALENESS_DAYS = 5
DEFAULT_MIN_COVERAGE_RATIO = 0.95


def _as_utc_timestamp(value: datetime | pd.Timestamp | None) -> pd.Timestamp:
    timestamp = pd.Timestamp(value if value is not None else datetime.now(UTC))
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def _asset_quality(
    prices: pd.DataFrame,
    symbol: str,
    *,
    minimum_history: int,
    source: str,
    generated_at: pd.Timestamp,
    max_staleness_days: int,
    min_coverage_ratio: float,
) -> MarketDataAssetQuality:
    if symbol not in prices:
        valid_dates = pd.DatetimeIndex([])
    else:
        values = pd.to_numeric(prices[symbol], errors="coerce")
        values = values.replace([float("inf"), float("-inf")], pd.NA)
        parsed_dates = pd.to_datetime(values.index, errors="coerce", utc=True)
        valid_mask = values.notna().to_numpy() & pd.notna(parsed_dates)
        valid_dates = pd.DatetimeIndex(parsed_dates[valid_mask]).normalize().unique().sort_values()

    observations = len(valid_dates)
    if not observations:
        return MarketDataAssetQuality(
            symbol=symbol,
            status=MarketDataQualityStatus.UNAVAILABLE,
            source="unavailable",
            observations=0,
            expected_sessions=0,
            missing_sessions=0,
            coverage_ratio=0.0,
            first_observation=None,
            last_observation=None,
            age_days=None,
        )

    first = valid_dates[0]
    last = valid_dates[-1]
    expected_dates = pd.bdate_range(
        first.tz_localize(None).normalize(),
        last.tz_localize(None).normalize(),
    )
    observed_business_dates = {
        timestamp.tz_localize(None).date() for timestamp in valid_dates if timestamp.weekday() < 5
    }
    missing_sessions = sum(
        expected.date() not in observed_business_dates for expected in expected_dates
    )
    expected_sessions = len(expected_dates)
    coverage_ratio = (
        (expected_sessions - missing_sessions) / expected_sessions if expected_sessions else 1.0
    )
    age_days = max((generated_at.normalize() - last.normalize()).days, 0)

    if observations < minimum_history:
        status = MarketDataQualityStatus.INSUFFICIENT
    elif age_days > max_staleness_days:
        status = MarketDataQualityStatus.STALE
    elif coverage_ratio < min_coverage_ratio:
        status = MarketDataQualityStatus.DEGRADED
    else:
        status = MarketDataQualityStatus.HEALTHY

    return MarketDataAssetQuality(
        symbol=symbol,
        status=status,
        source=source,
        observations=observations,
        expected_sessions=expected_sessions,
        missing_sessions=missing_sessions,
        coverage_ratio=coverage_ratio,
        first_observation=first.to_pydatetime(),
        last_observation=last.to_pydatetime(),
        age_days=age_days,
    )


def assess_market_data_quality(
    prices: pd.DataFrame,
    symbols: Iterable[str],
    *,
    minimum_history: int,
    provider: str,
    sources: Mapping[str, str] | None = None,
    errors: Mapping[str, str] | None = None,
    now: datetime | pd.Timestamp | None = None,
    max_staleness_days: int = DEFAULT_MAX_STALENESS_DAYS,
    min_coverage_ratio: float = DEFAULT_MIN_COVERAGE_RATIO,
) -> MarketDataQualityReport:
    if minimum_history < 1:
        raise ValueError("El mínimo de observaciones debe ser positivo")
    if max_staleness_days < 0:
        raise ValueError("La tolerancia de frescura no puede ser negativa")
    if not 0 < min_coverage_ratio <= 1:
        raise ValueError("La cobertura mínima debe estar entre 0 y 1")

    generated_at = _as_utc_timestamp(now)
    normalized_symbols = list(
        dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip())
    )
    source_map = {str(key).strip().upper(): value for key, value in (sources or {}).items()}
    failed_symbols = {str(key).strip().upper() for key in (errors or {})}
    assets = {
        symbol: _asset_quality(
            prices,
            symbol,
            minimum_history=minimum_history,
            source=(
                "unavailable" if symbol in failed_symbols else source_map.get(symbol, "provider")
            ),
            generated_at=generated_at,
            max_staleness_days=max_staleness_days,
            min_coverage_ratio=min_coverage_ratio,
        )
        for symbol in normalized_symbols
    }

    statuses = [quality.status for quality in assets.values()]
    if not statuses or all(status is MarketDataQualityStatus.UNAVAILABLE for status in statuses):
        status = MarketDataQualityStatus.UNAVAILABLE
    elif all(status is MarketDataQualityStatus.HEALTHY for status in statuses):
        status = MarketDataQualityStatus.HEALTHY
    else:
        status = MarketDataQualityStatus.DEGRADED

    return MarketDataQualityReport(
        provider=provider,
        status=status,
        assets=assets,
        generated_at=generated_at.to_pydatetime(),
    )
