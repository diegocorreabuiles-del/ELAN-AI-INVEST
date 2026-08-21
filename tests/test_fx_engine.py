from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from elan_ai_invest.fx import (
    FxPair,
    FxRoutingEngine,
    FxSourceType,
    HistoricalFxService,
    ProviderHistory,
    ProviderPair,
    build_virtual_fx_catalog,
    calculate_cross_rate,
    compute_fx_kpis,
    correlation_statistics,
    invert_fx_rate,
    load_currency_registry,
    normalize_fx_pair,
    search_fx_pairs,
    validate_inverse_consistency,
    validate_triangular_consistency,
)
from elan_ai_invest.market.cache import MarketCache
from elan_ai_invest.market_data import download_market_history


def _history(values: list[float], dates: pd.DatetimeIndex | None = None) -> pd.DataFrame:
    index = dates if dates is not None else pd.bdate_range("2026-01-01", periods=len(values))
    close = pd.Series(values, index=index, dtype=float)
    return pd.DataFrame(
        {
            "Open": close * 0.995,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": 0.0,
        },
        index=index,
    )


class FakeFxProvider:
    def __init__(
        self,
        *,
        pairs: dict[str, ProviderHistory] | None = None,
        symbols: dict[str, ProviderHistory] | None = None,
    ) -> None:
        self.pairs = pairs or {}
        self.symbols = symbols or {}
        self.calls: list[str] = []

    def load_pair(
        self,
        pair: FxPair,
        *,
        period: str,
        interval: str,
    ) -> ProviderHistory | None:
        self.calls.append(pair.display)
        return self.pairs.get(pair.display)

    def load_provider_pair(
        self,
        pair: ProviderPair,
        *,
        period: str,
        interval: str,
    ) -> ProviderHistory | None:
        self.calls.append(pair.symbol)
        return self.symbols.get(pair.symbol)


def _provider_history(
    symbol: str,
    base: str,
    quote: str,
    values: list[float],
    dates: pd.DatetimeIndex | None = None,
) -> ProviderHistory:
    return ProviderHistory(
        provider_pair=ProviderPair("Yahoo", symbol, base, quote),
        prices=_history(values, dates),
        received_at=datetime(2026, 8, 14, tzinfo=UTC),
    )


def _service(
    *,
    pairs: dict[str, ProviderHistory] | None = None,
    symbols: dict[str, ProviderHistory] | None = None,
) -> tuple[HistoricalFxService, FakeFxProvider]:
    provider = FakeFxProvider(pairs=pairs, symbols=symbols)
    registry = load_currency_registry()
    return HistoricalFxService(registry, provider), provider


def test_registry_contains_requested_global_and_latam_currencies() -> None:
    registry = load_currency_registry()

    assert len(registry.codes()) == 36
    assert {
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "COP",
        "MXN",
        "CLP",
        "BRL",
        "PEN",
        "UYU",
        "PYG",
        "BOB",
        "CRC",
        "DOP",
        "GTQ",
        "HNL",
        "AED",
        "SAR",
    } <= set(registry.codes())


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("EUR/COP", FxPair("EUR", "COP")),
        ("eurcop", FxPair("EUR", "COP")),
        ("FX_EUR_COP", FxPair("EUR", "COP")),
    ],
)
def test_pair_normalization_uses_internal_provider_independent_id(
    raw: str,
    expected: FxPair,
) -> None:
    pair = normalize_fx_pair(raw)

    assert pair == expected
    assert pair.asset_id == "FX_EUR_COP"


def test_required_case_1_builds_eur_cop_via_usd() -> None:
    service, _ = _service(
        symbols={
            "EURUSD=X": _provider_history("EURUSD=X", "EUR", "USD", [1.10, 1.10]),
            "COP=X": _provider_history("COP=X", "USD", "COP", [4_000.0, 4_000.0]),
        }
    )

    result = service.get_history(FxPair("EUR", "COP"))

    assert result.prices["Close"].iloc[-1] == pytest.approx(4_400.0)
    assert result.route.source_type is FxSourceType.SYNTHETIC
    assert result.route.currency_path == ("EUR", "USD", "COP")
    assert result.route.calculation_path == "EUR/USD × USD/COP"


def test_required_case_2_inverts_usd_cop_without_redownload() -> None:
    service, provider = _service(
        symbols={"COP=X": _provider_history("COP=X", "USD", "COP", [4_000.0, 4_000.0])}
    )

    result = service.get_history(FxPair("COP", "USD"))

    assert result.prices["Close"].iloc[-1] == pytest.approx(0.00025)
    assert result.route.source_type is FxSourceType.INVERSE
    assert provider.calls.count("COP=X") == 1


def test_required_case_3_builds_mxn_cop_with_correct_orientation() -> None:
    service, _ = _service(
        symbols={
            "MXN=X": _provider_history("MXN=X", "USD", "MXN", [20.0, 20.0]),
            "COP=X": _provider_history("COP=X", "USD", "COP", [4_000.0, 4_000.0]),
        }
    )

    result = service.get_history(FxPair("MXN", "COP"))

    assert result.prices["Close"].iloc[-1] == pytest.approx(200.0)
    assert result.route.currency_path == ("MXN", "USD", "COP")


def test_required_case_4_inverts_direct_eur_cop() -> None:
    direct = _provider_history("EURCOP=X", "EUR", "COP", [4_400.0, 4_400.0])
    service, _ = _service(pairs={"EUR/COP": direct})

    result = service.get_history(FxPair("COP", "EUR"))

    assert result.prices["Close"].iloc[-1] == pytest.approx(1 / 4_400.0)
    assert result.route.source_type is FxSourceType.INVERSE


def test_required_case_5_synthetic_history_uses_inner_date_alignment() -> None:
    eur_dates = pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-06"])
    cop_dates = pd.to_datetime(["2026-01-02", "2026-01-06", "2026-01-07"])
    service, _ = _service(
        symbols={
            "EURUSD=X": _provider_history("EURUSD=X", "EUR", "USD", [1.1, 1.2, 1.3], eur_dates),
            "COP=X": _provider_history("COP=X", "USD", "COP", [4_000, 4_100, 4_200], cop_dates),
        }
    )

    result = service.get_history(FxPair("EUR", "COP"))

    assert result.prices.index.strftime("%Y-%m-%d").tolist() == ["2026-01-02", "2026-01-06"]
    assert result.prices["Close"].tolist() == pytest.approx([4_400.0, 5_330.0])
    assert result.coverage_ratio == pytest.approx(0.5)


def test_required_case_6_correlation_excludes_missing_dates_and_reports_coverage() -> None:
    first = pd.Series(
        [100.0, 101.0, 102.0, 104.0],
        index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-05", "2026-01-06"]),
    )
    second = pd.Series(
        [200.0, 202.0, 208.0, 210.0],
        index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-06", "2026-01-07"]),
    )

    stats = correlation_statistics(first, second)

    assert stats.observations == 2
    assert stats.coverage_ratio == pytest.approx(3 / 5)
    assert stats.start_date == pd.Timestamp("2026-01-02", tz="UTC")
    assert stats.end_date == pd.Timestamp("2026-01-06", tz="UTC")


def test_required_case_7_uses_registered_fallback_when_generic_pair_is_unavailable() -> None:
    service, provider = _service(
        symbols={"COP=X": _provider_history("COP=X", "USD", "COP", [4_000.0, 4_050.0])}
    )

    result = service.get_history(FxPair("USD", "COP"))

    assert result.prices["Close"].iloc[-1] == pytest.approx(4_050.0)
    assert result.route.source_type is FxSourceType.DIRECT
    assert provider.calls[:2] == ["USD/COP", "COP/USD"]
    assert "COP=X" in provider.calls


def test_required_case_8_flags_inconsistent_direct_and_synthetic_rate() -> None:
    incident = validate_triangular_consistency(4_900.0, 1.1 * 4_000.0, tolerance=0.01)

    assert incident is not None
    assert incident.code == "TRIANGULAR_DEVIATION"
    assert incident.severity == "high"


def test_rate_helpers_fail_closed_for_invalid_values() -> None:
    assert calculate_cross_rate(1.10, 4_000.0) == pytest.approx(4_400.0)
    assert invert_fx_rate(4_000.0) == pytest.approx(0.00025)
    assert validate_inverse_consistency(4_000.0, 0.00025) is None
    with pytest.raises(ValueError, match="positiva"):
        invert_fx_rate(0.0)
    with pytest.raises(ValueError, match="positivas"):
        calculate_cross_rate(1.0, np.nan)


def test_routing_prefers_short_liquid_usd_bridge() -> None:
    routing = FxRoutingEngine(load_currency_registry())

    route = routing.resolve(FxPair("COP", "MXN"))

    assert route.source_type is FxSourceType.SYNTHETIC
    assert route.currency_path == ("COP", "USD", "MXN")
    assert len(route.legs) == 2


def test_virtual_catalog_searches_code_name_country_and_pair() -> None:
    catalog = build_virtual_fx_catalog(load_currency_registry())

    by_code = search_fx_pairs(catalog, "COP", limit=20)
    by_name = search_fx_pairs(catalog, "peso colombiano", limit=20)
    exact = search_fx_pairs(catalog, "EUR/COP", limit=5)

    required = {"FX_USD_COP", "FX_COP_USD", "FX_EUR_COP", "FX_COP_EUR"}
    assert required <= set(by_code["asset_id"])
    assert required <= set(by_name["asset_id"])
    assert exact.iloc[0]["asset_id"] == "FX_EUR_COP"


def test_kpis_preserve_precision_and_produce_fx_indicators() -> None:
    values = (1.0 + np.linspace(0.0, 0.30, 260)).tolist()

    kpis = compute_fx_kpis(_history(values))

    assert kpis.latest == pytest.approx(1.30)
    assert kpis.change_1d_pct is not None
    assert kpis.change_1y_pct is not None
    assert kpis.sma_50 is not None
    assert kpis.sma_200 is not None
    assert kpis.rsi_14 == pytest.approx(100.0)
    assert kpis.atr_14 is not None
    assert kpis.trend == "Alcista"


def test_market_history_uses_persistent_csv_cache(tmp_path: Path) -> None:
    calls = 0

    def downloader(*args, **kwargs) -> pd.DataFrame:
        nonlocal calls
        del args, kwargs
        calls += 1
        return _history([1.0, 1.1, 1.2])

    cache = MarketCache(tmp_path / "fx-cache", ttl_seconds=3_600)
    first = download_market_history("EURUSD=X", downloader=downloader, cache=cache)
    second = download_market_history(
        "EURUSD=X",
        downloader=lambda *args, **kwargs: pytest.fail("No debe repetir la descarga"),
        cache=cache,
    )

    assert calls == 1
    pd.testing.assert_frame_equal(first, second, check_freq=False)
