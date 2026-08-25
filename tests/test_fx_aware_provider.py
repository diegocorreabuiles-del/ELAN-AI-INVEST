from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pandas as pd

from elan_ai_invest.market.quality import assess_market_data_quality
from elan_ai_invest.providers.base import DownloadResult
from elan_ai_invest.providers.fx_aware import FxAwareMarketDataProvider


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def download_prices(self, symbols, period, interval="1d", minimum_history=60):
        requested = list(symbols)
        self.calls.append(requested)
        index = pd.date_range("2026-01-01", periods=70, freq="B")
        prices = pd.DataFrame(
            {symbol: range(100, 170) for symbol in requested},
            index=index,
        )
        quality = assess_market_data_quality(
            prices,
            requested,
            minimum_history=minimum_history,
            provider="fake",
        )
        return DownloadResult(prices=prices, errors={}, quality=quality)


class FakeFxHistory:
    def __init__(self, *, fail: bool = False, observations: int = 70) -> None:
        self.fail = fail
        self.observations = observations
        self.calls: list[str] = []

    def get_history(self, pair, *, period, interval):
        self.calls.append(pair.asset_id)
        if self.fail:
            raise ValueError("ruta FX no disponible")
        index = pd.date_range(
            "2026-01-01",
            periods=self.observations,
            freq="B",
            tz="UTC",
        )
        prices = pd.DataFrame(
            {
                "Open": range(1, self.observations + 1),
                "High": range(2, self.observations + 2),
                "Low": [value + 0.5 for value in range(self.observations)],
                "Close": [value + 1.0 for value in range(self.observations)],
                "Volume": 0.0,
            },
            index=index,
        )
        route = SimpleNamespace(
            source_type=SimpleNamespace(value="SYNTHETIC"),
            provider="Test FX",
            calculation_path="EUR/USD × USD/GBP",
        )
        return SimpleNamespace(
            prices=prices,
            route=route,
            coverage_ratio=0.97,
            received_at=datetime(2026, 4, 10, 12, tzinfo=UTC),
        )


def test_fx_aware_provider_combines_regular_and_virtual_fx() -> None:
    regular = FakeProvider()
    fx_history = FakeFxHistory()
    provider = FxAwareMarketDataProvider(regular, fx_history)

    result = provider.download_prices(
        ["AAPL", "FX_EUR_GBP"],
        period="1y",
        minimum_history=60,
    )

    assert regular.calls == [["AAPL"]]
    assert fx_history.calls == ["FX_EUR_GBP"]
    assert list(result.prices.columns) == ["AAPL", "FX_EUR_GBP"]
    assert result.prices.index.tz is None
    assert result.errors == {}
    assert result.quality is not None
    fx_quality = result.quality.assets["FX_EUR_GBP"]
    assert fx_quality.source == "fx:synthetic"
    assert fx_quality.route_provider == "Test FX"
    assert fx_quality.route_path == "EUR/USD × USD/GBP"
    assert fx_quality.route_coverage_ratio == 0.97
    assert fx_quality.received_at == datetime(2026, 4, 10, 12, tzinfo=UTC)


def test_fx_aware_provider_does_not_call_regular_provider_for_fx_only() -> None:
    regular = FakeProvider()
    provider = FxAwareMarketDataProvider(regular, FakeFxHistory())

    result = provider.download_prices(["FX_COP_MXN"], period="1y", minimum_history=60)

    assert regular.calls == []
    assert list(result.prices.columns) == ["FX_COP_MXN"]


def test_fx_aware_provider_reports_fx_failure_without_losing_regular_prices() -> None:
    regular = FakeProvider()
    provider = FxAwareMarketDataProvider(regular, FakeFxHistory(fail=True))

    result = provider.download_prices(
        ["AAPL", "FX_NGN_XOF"],
        period="1y",
        minimum_history=60,
    )

    assert list(result.prices.columns) == ["AAPL"]
    assert "ruta FX no disponible" in result.errors["FX_NGN_XOF"]
    assert result.quality is not None
    assert result.quality.assets["FX_NGN_XOF"].source == "unavailable"


def test_fx_aware_provider_rejects_insufficient_fx_history() -> None:
    provider = FxAwareMarketDataProvider(FakeProvider(), FakeFxHistory(observations=10))

    result = provider.download_prices(["FX_EUR_USD"], period="1mo", minimum_history=20)

    assert result.prices.empty
    assert "Historico insuficiente" in result.errors["FX_EUR_USD"]
