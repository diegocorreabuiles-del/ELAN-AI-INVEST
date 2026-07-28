from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from elan_ai_invest.dashboard.market import _history_chart, build_comparison_data
from elan_ai_invest.market_data import download_market_history


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
