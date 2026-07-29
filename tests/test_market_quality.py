from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from elan_ai_invest.market.quality import assess_market_data_quality
from elan_ai_invest.providers.base import MarketDataQualityStatus

NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)


def _prices(index: pd.DatetimeIndex, symbol: str = "SPY") -> pd.DataFrame:
    return pd.DataFrame({symbol: range(100, 100 + len(index))}, index=index)


def test_quality_report_marks_recent_complete_history_as_healthy() -> None:
    index = pd.bdate_range(end="2026-07-27", periods=10)

    report = assess_market_data_quality(
        _prices(index),
        ["SPY"],
        minimum_history=5,
        provider="Yahoo",
        sources={"SPY": "provider"},
        now=NOW,
    )

    quality = report.assets["SPY"]
    assert report.status is MarketDataQualityStatus.HEALTHY
    assert quality.status is MarketDataQualityStatus.HEALTHY
    assert quality.source == "provider"
    assert quality.observations == 10
    assert quality.missing_sessions == 0
    assert quality.coverage_ratio == pytest.approx(1.0)
    assert quality.age_days == 1


def test_quality_report_detects_internal_gaps_without_filling_prices() -> None:
    complete_index = pd.bdate_range("2026-07-13", "2026-07-24")
    incomplete_index = complete_index.delete([2, 6])
    prices = _prices(incomplete_index)

    report = assess_market_data_quality(
        prices,
        ["SPY"],
        minimum_history=5,
        provider="Yahoo",
        now=NOW,
    )

    quality = report.assets["SPY"]
    assert quality.status is MarketDataQualityStatus.DEGRADED
    assert quality.missing_sessions == 2
    assert quality.coverage_ratio == pytest.approx(0.8)
    assert prices.index.equals(incomplete_index)


def test_quality_report_distinguishes_stale_and_unavailable_assets() -> None:
    stale_index = pd.bdate_range(end="2026-07-10", periods=10)

    report = assess_market_data_quality(
        _prices(stale_index, "AAPL"),
        ["AAPL", "OFFLINE"],
        minimum_history=5,
        provider="Yahoo",
        sources={"AAPL": "cache"},
        errors={"OFFLINE": "timeout controlado"},
        now=NOW,
    )

    assert report.status is MarketDataQualityStatus.DEGRADED
    assert report.assets["AAPL"].status is MarketDataQualityStatus.STALE
    assert report.assets["AAPL"].source == "cache"
    assert report.assets["OFFLINE"].status is MarketDataQualityStatus.UNAVAILABLE
    assert report.assets["OFFLINE"].observations == 0


def test_quality_report_marks_short_history_as_insufficient() -> None:
    index = pd.bdate_range(end="2026-07-27", periods=3)

    report = assess_market_data_quality(
        _prices(index),
        ["SPY"],
        minimum_history=5,
        provider="Yahoo",
        now=NOW,
    )

    assert report.assets["SPY"].status is MarketDataQualityStatus.INSUFFICIENT
