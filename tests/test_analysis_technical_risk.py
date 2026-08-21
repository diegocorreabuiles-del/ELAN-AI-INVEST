from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from elan_ai_invest.analysis import (
    calculate_market_metrics,
    calculate_risk_metrics,
    calculate_technical_metrics,
    consecutive_returns,
)


def _history(close: np.ndarray, volume: np.ndarray | None = None) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=len(close), freq="B")
    movement = np.maximum(np.abs(np.gradient(close)), close * 0.002)
    return pd.DataFrame(
        {
            "Open": close - movement * 0.2,
            "High": close + movement,
            "Low": close - movement,
            "Close": close,
            "Volume": volume if volume is not None else np.full(len(close), 1_000_000.0),
        },
        index=dates,
    )


def test_bullish_history_produces_complete_explainable_technical_metrics() -> None:
    close = np.linspace(100.0, 180.0, 300) + np.sin(np.arange(300) / 8)
    volume = np.linspace(800_000.0, 1_600_000.0, 300)
    metrics = calculate_technical_metrics(_history(close, volume))

    assert metrics.score is not None and 0 <= metrics.score <= 100
    assert metrics.trend_score == 100.0
    assert metrics.sma_50 is not None and metrics.sma_200 is not None
    assert metrics.ema_200 is not None and metrics.rsi_14 is not None
    assert metrics.macd is not None and metrics.adx_14 is not None
    assert metrics.atr_14 is not None and metrics.rvol_20 is not None
    assert metrics.price_vs_sma_50_pct is not None
    assert metrics.price_vs_sma_200_pct is not None
    assert metrics.support is not None and metrics.resistance is not None


def test_bearish_history_has_lower_trend_score_than_bullish_history() -> None:
    bullish = calculate_technical_metrics(_history(np.linspace(100.0, 180.0, 300)))
    bearish = calculate_technical_metrics(_history(np.linspace(180.0, 100.0, 300)))

    assert bullish.trend_score is not None and bearish.trend_score is not None
    assert bullish.trend_score > bearish.trend_score


def test_sideways_history_keeps_scores_bounded_without_directional_claims() -> None:
    close = 100.0 + np.sin(np.arange(300) / 4.0)

    metrics = calculate_technical_metrics(_history(close))

    assert metrics.score is not None and 0 <= metrics.score <= 100
    assert metrics.trend_score is not None and 0 <= metrics.trend_score <= 100
    assert metrics.momentum_score is not None and 0 <= metrics.momentum_score <= 100


def test_market_metrics_use_observed_returns_and_liquidity() -> None:
    metrics = calculate_market_metrics(_history(np.linspace(100.0, 130.0, 300)))

    assert metrics.price == pytest.approx(130.0)
    assert metrics.change_1d_pct is not None and metrics.change_7d_pct is not None
    assert metrics.change_30d_pct is not None and metrics.change_1y_pct is not None
    assert metrics.average_volume_20d == pytest.approx(1_000_000.0)
    assert metrics.average_dollar_volume is not None
    assert metrics.market_cap is None


def test_short_history_returns_partial_metrics_instead_of_neutral_scores() -> None:
    history = _history(np.linspace(100.0, 103.0, 15))
    technical = calculate_technical_metrics(history)
    risk = calculate_risk_metrics(history)

    assert technical.score is None and technical.rsi_14 is None
    assert risk.score is None and risk.annual_volatility_pct is None


def test_risk_metrics_measure_beta_correlation_and_remain_bounded() -> None:
    rng = np.random.default_rng(7)
    benchmark_returns = rng.normal(0.0004, 0.008, 300)
    asset_returns = benchmark_returns * 1.8
    benchmark_close = 100.0 * np.cumprod(1.0 + benchmark_returns)
    asset_close = 100.0 * np.cumprod(1.0 + asset_returns)

    metrics = calculate_risk_metrics(_history(asset_close), _history(benchmark_close))

    assert metrics.score is not None and 0 <= metrics.score <= 100
    assert metrics.beta == pytest.approx(1.8, rel=0.03)
    assert metrics.benchmark_correlation == pytest.approx(1.0)
    assert metrics.annual_volatility_pct is not None and metrics.annual_volatility_pct > 0
    assert metrics.var_95_daily_pct is not None and metrics.var_95_daily_pct >= 0
    assert metrics.maximum_drawdown_pct is not None and metrics.maximum_drawdown_pct <= 0
    assert metrics.atr_pct is not None and metrics.atr_pct > 0


def test_extreme_volatility_reduces_risk_score() -> None:
    rng = np.random.default_rng(11)
    calm = 100.0 * np.cumprod(1.0 + rng.normal(0.0003, 0.004, 300))
    volatile = 100.0 * np.cumprod(1.0 + rng.normal(0.0003, 0.04, 300))
    calm_risk = calculate_risk_metrics(_history(calm))
    volatile_risk = calculate_risk_metrics(_history(volatile))

    assert calm_risk.score is not None and volatile_risk.score is not None
    assert calm_risk.score > volatile_risk.score


def test_missing_session_is_not_forward_filled_for_benchmark_metrics() -> None:
    rng = np.random.default_rng(21)
    returns = rng.normal(0.0003, 0.01, 100)
    close = 100.0 * np.cumprod(1.0 + returns)
    asset = _history(close)
    benchmark = _history(close.copy())
    benchmark.loc[benchmark.index[40], "Close"] = np.nan

    metrics = calculate_risk_metrics(asset, benchmark)

    assert metrics.beta == pytest.approx(1.0)
    assert metrics.benchmark_correlation == pytest.approx(1.0)


def test_missing_asset_session_does_not_create_a_return_across_the_gap() -> None:
    history = _history(np.linspace(100.0, 120.0, 100))
    missing_date = history.index[40]
    following_date = history.index[41]
    history.loc[missing_date, "Close"] = np.nan

    returns = consecutive_returns(history)

    assert missing_date not in returns.index
    assert following_date not in returns.index
    assert len(returns) == len(history) - 3


def test_risk_engine_uses_only_consecutive_returns_with_missing_asset_session() -> None:
    history = _history(np.linspace(100.0, 120.0, 100))
    history.loc[history.index[40], "Close"] = np.nan

    metrics = calculate_risk_metrics(history)
    expected = consecutive_returns(history)

    assert len(expected) == len(history) - 3
    assert metrics.annual_volatility_pct == pytest.approx(
        expected.std(ddof=1) * np.sqrt(252) * 100.0
    )


def test_invalid_ohlc_contract_fails_explicitly() -> None:
    with pytest.raises(ValueError, match="Faltan columnas OHLC"):
        calculate_technical_metrics(pd.DataFrame({"Close": [100.0, 101.0]}))
