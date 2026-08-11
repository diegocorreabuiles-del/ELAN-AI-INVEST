from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from elan_ai_invest.dashboard.forex import (
    _correlation_figure,
    _performance_figure,
    _rolling_figure,
)
from elan_ai_invest.forex import build_forex_analysis, normalize_fx_prices


def test_fx_normalization_uses_usd_per_currency_unit() -> None:
    index = pd.bdate_range("2026-01-01", periods=3)
    raw = pd.DataFrame(
        {
            "EURUSD=X": [1.10, 1.20, 1.15],
            "JPY=X": [100.0, 125.0, 80.0],
            "COP=X": [4_000.0, 5_000.0, 0.0],
        },
        index=index,
    )

    result = normalize_fx_prices(raw, ("EUR", "JPY", "COP"))

    assert result["EUR"].tolist() == pytest.approx([1.10, 1.20, 1.15])
    assert result["JPY"].tolist() == pytest.approx([0.01, 0.008, 0.0125])
    assert result["COP"].iloc[:2].tolist() == pytest.approx([0.00025, 0.0002])
    assert pd.isna(result["COP"].iloc[2])


def test_fx_analysis_uses_common_aligned_returns_without_filling() -> None:
    index = pd.bdate_range("2026-01-01", periods=80)
    base_returns = np.linspace(-0.01, 0.01, len(index))
    prices = pd.DataFrame(
        {
            "EUR": np.cumprod(1 + base_returns),
            "GBP": np.cumprod(1 + base_returns * 0.8),
            "JPY": np.cumprod(1 - base_returns),
        },
        index=index,
    )
    prices.loc[index[20], "JPY"] = np.nan

    result = build_forex_analysis(prices, "EUR", "JPY", window=20)

    assert result.normalized.iloc[0].tolist() == pytest.approx([100.0, 100.0, 100.0])
    assert len(result.returns) == 78
    assert result.correlation.loc["EUR", "GBP"] > 0.99
    assert result.correlation.loc["EUR", "JPY"] < -0.99
    assert result.rolling_correlation.between(-1, 1).all()
    assert result.summary["currency"].tolist() == ["EUR", "GBP", "JPY"]


def test_fx_analysis_rejects_invalid_focus_or_window() -> None:
    prices = pd.DataFrame({"EUR": [1.0, 1.1, 1.2], "GBP": [1.0, 1.2, 1.3]})

    with pytest.raises(ValueError, match="distintas"):
        build_forex_analysis(prices, "EUR", "EUR")
    with pytest.raises(ValueError, match="no tiene datos"):
        build_forex_analysis(prices, "EUR", "JPY")
    with pytest.raises(ValueError, match="al menos 2"):
        build_forex_analysis(prices, "EUR", "GBP", window=1)


def test_fx_figures_avoid_webgl_traces() -> None:
    index = pd.bdate_range("2025-01-01", periods=100)
    prices = pd.DataFrame(
        {
            "EUR": 1.1 + np.arange(len(index)) * 0.001,
            "GBP": 1.3 + np.arange(len(index)) * 0.0015,
        },
        index=index,
    )
    analysis = build_forex_analysis(prices, "EUR", "GBP", window=20)

    performance = _performance_figure(analysis)
    matrix = _correlation_figure(analysis)
    rolling = _rolling_figure(analysis, "EUR", "GBP", 20)

    assert all(trace.type == "scatter" for trace in performance.data)
    assert [trace.type for trace in matrix.data] == ["heatmap"]
    assert [trace.type for trace in rolling.data] == ["scatter"]
