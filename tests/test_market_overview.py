from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from elan_ai_invest.dashboard.market import (
    MAX_COMPARISON_INSTRUMENTS,
    _history_chart,
    _multi_comparison_figures,
    _quality_rows,
    _reference_rolling_figure,
    _resample_history_for_chart,
    build_comparison_data,
    build_multi_comparison_data,
    build_reference_correlation_data,
)
from elan_ai_invest.market_data import download_market_history
from elan_ai_invest.providers.base import (
    MarketDataAssetQuality,
    MarketDataQualityReport,
    MarketDataQualityStatus,
)


def _ohlcv_frame(rows: int = 65) -> pd.DataFrame:
    index = pd.bdate_range("2025-01-01", periods=rows)
    close = pd.Series(100 + np.arange(rows, dtype=float), index=index)
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": 1_000 + np.arange(rows),
        },
        index=index,
    )


def test_quality_rows_exposes_fx_route_provenance() -> None:
    generated_at = datetime(2026, 8, 25, 12, tzinfo=UTC)
    report = MarketDataQualityReport(
        provider="Yahoo + FX routing",
        status=MarketDataQualityStatus.HEALTHY,
        assets={
            "FX_EUR_COP": MarketDataAssetQuality(
                symbol="FX_EUR_COP",
                status=MarketDataQualityStatus.HEALTHY,
                source="fx:synthetic",
                observations=250,
                expected_sessions=250,
                missing_sessions=0,
                coverage_ratio=1.0,
                first_observation=datetime(2025, 8, 25, tzinfo=UTC),
                last_observation=datetime(2026, 8, 24, tzinfo=UTC),
                age_days=1,
                route_provider="Yahoo",
                route_path="EUR/USD × USD/COP",
                route_coverage_ratio=0.98,
                received_at=generated_at,
            )
        },
        generated_at=generated_at,
    )

    row = _quality_rows(report)[0]

    assert row["Origen"] == "FX sintética"
    assert row["Proveedor de ruta"] == "Yahoo"
    assert row["Ruta FX"] == "EUR/USD × USD/COP"
    assert row["Cobertura de ruta"] == "98.0%"


def test_download_market_history_normalizes_multiindex_and_retries() -> None:
    calls: list[dict] = []
    delays: list[float] = []
    source = _ohlcv_frame()
    source.columns = pd.MultiIndex.from_product([source.columns, ["AAPL"]])

    def downloader(symbol, **kwargs):
        calls.append({"symbol": symbol, **kwargs})
        if len(calls) == 1:
            raise TimeoutError("temporal")
        return source

    result = download_market_history(
        "aapl",
        period="5y",
        timeout_seconds=7.0,
        max_retries=1,
        backoff_seconds=0.25,
        downloader=downloader,
        sleep=delays.append,
    )

    assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(result) == 65
    assert calls[-1]["symbol"] == "AAPL"
    assert calls[-1]["period"] == "5y"
    assert calls[-1]["auto_adjust"] is True
    assert calls[-1]["actions"] is False
    assert calls[-1]["timeout"] == 7.0
    assert delays == [0.25]


def test_download_market_history_reports_exhausted_attempts() -> None:
    def downloader(symbol, **kwargs):
        del symbol, kwargs
        raise TimeoutError("sin respuesta")

    with pytest.raises(RuntimeError, match="tras 2 intentos: sin respuesta"):
        download_market_history(
            "EURUSD=X",
            max_retries=1,
            backoff_seconds=0,
            downloader=downloader,
            sleep=lambda _: None,
        )


def test_comparison_uses_aligned_consecutive_returns_without_filling() -> None:
    index = pd.bdate_range("2026-01-01", periods=80)
    first_returns = np.linspace(-0.01, 0.01, len(index))
    second_returns = -first_returns
    prices = pd.DataFrame(
        {
            "EURUSD=X": 100 * np.cumprod(1 + first_returns),
            "DX-Y.NYB": 100 * np.cumprod(1 + second_returns),
        },
        index=index,
    )
    prices.loc[index[20], "DX-Y.NYB"] = np.nan

    result = build_comparison_data(prices, "EURUSD=X", "DX-Y.NYB", window=20)

    assert result.normalized.iloc[0].tolist() == pytest.approx([100.0, 100.0])
    assert len(result.returns) == 78
    assert result.correlation < -0.99
    assert result.rolling_correlation.between(-1, 1).all()


def test_comparison_rejects_same_or_unavailable_instruments() -> None:
    prices = pd.DataFrame({"AAPL": [100.0, 101.0, 102.0]})

    with pytest.raises(ValueError, match="distintos"):
        build_comparison_data(prices, "AAPL", "AAPL")
    with pytest.raises(ValueError, match="no tiene datos"):
        build_comparison_data(prices, "AAPL", "MSFT")


def test_multi_comparison_uses_common_sessions_without_filling() -> None:
    index = pd.bdate_range("2026-01-01", periods=80)
    base_returns = np.linspace(-0.01, 0.01, len(index))
    prices = pd.DataFrame(
        {
            "AAPL": 100 * np.cumprod(1 + base_returns),
            "MSFT": 100 * np.cumprod(1 + base_returns * 0.8),
            "BTC-USD": 100 * np.cumprod(1 - base_returns),
        },
        index=index,
    )
    prices.loc[index[20], "BTC-USD"] = np.nan

    result = build_multi_comparison_data(prices, ["AAPL", "MSFT", "BTC-USD"])

    assert MAX_COMPARISON_INSTRUMENTS == 8
    assert result.normalized.iloc[0].tolist() == pytest.approx([100.0, 100.0, 100.0])
    assert len(result.returns) == 78
    assert result.correlation.shape == (3, 3)
    performance, matrix = _multi_comparison_figures(result)
    assert all(trace.type == "scatter" for trace in performance.data)
    assert [trace.type for trace in matrix.data] == ["heatmap"]


def test_reference_correlations_include_every_other_focal_instrument() -> None:
    index = pd.bdate_range("2026-01-01", periods=80)
    returns = pd.DataFrame(
        {
            "AAPL": np.linspace(-0.01, 0.01, len(index)),
            "MSFT": np.linspace(-0.008, 0.008, len(index)),
            "BTC-USD": np.linspace(0.01, -0.01, len(index)),
        },
        index=index,
    )

    correlations, rolling = build_reference_correlation_data(
        returns,
        "AAPL",
        ["AAPL", "MSFT", "BTC-USD"],
        window=20,
    )
    figure = _reference_rolling_figure(rolling, "AAPL", 20)

    assert list(correlations.index) == ["MSFT", "BTC-USD"]
    assert list(rolling.columns) == ["AAPL / MSFT", "AAPL / BTC-USD"]
    assert correlations["MSFT"] > 0.99
    assert correlations["BTC-USD"] < -0.99
    assert len(figure.data) == 2
    assert all(trace.type == "scatter" for trace in figure.data)


@pytest.mark.parametrize(
    ("view", "trace_type"),
    [
        ("Velas", "candlestick"),
        ("Línea", "scatter"),
        ("Rentabilidad", "scatter"),
        ("Volumen", "bar"),
    ],
)
def test_popular_history_views_build_expected_chart(view: str, trace_type: str) -> None:
    chart = _history_chart(_ohlcv_frame(), "AAPL", view)

    assert chart.data[0].type == trace_type


def test_long_horizons_use_readable_ohlcv_aggregation() -> None:
    history = _ohlcv_frame(2_600)

    weekly = _resample_history_for_chart(history, "10y")
    monthly = _resample_history_for_chart(history, "max")

    assert 500 <= len(weekly) <= 530
    assert 115 <= len(monthly) <= 125
    assert weekly.iloc[0]["Open"] == history.iloc[0]["Open"]
    assert weekly.iloc[0]["High"] == history.loc[: weekly.index[0], "High"].max()
    assert weekly.iloc[0]["Low"] == history.loc[: weekly.index[0], "Low"].min()
    assert weekly.iloc[0]["Close"] == history.loc[: weekly.index[0], "Close"].iloc[-1]
    assert weekly.iloc[0]["Volume"] == history.loc[: weekly.index[0], "Volume"].sum()


def test_long_price_chart_supports_log_scale_and_preserves_endpoints() -> None:
    history = _ohlcv_frame(2_600)

    chart = _history_chart(
        history,
        "AAPL",
        "Línea",
        period="10y",
        price_scale="Logarítmica",
    )

    assert chart.layout.yaxis.type == "log"
    assert len(chart.data[0].x) < 550
    assert chart.data[0].x[0] == history.index[0]
    assert chart.data[0].y[0] == history["Close"].iloc[0]
    assert chart.data[0].x[-1] == history.index[-1]
    assert chart.data[0].y[-1] == history["Close"].iloc[-1]
