from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .models import RiskMetrics
from .technical import calculate_atr_adx, clean_ohlcv

_MINIMUM_RISK_RETURNS = 59


def _finite(value: float | np.floating | None) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _bounded(value: float) -> float:
    return float(np.clip(value, 0.0, 100.0))


def _close_series(data: pd.DataFrame | pd.Series) -> pd.Series:
    values = data["Close"] if isinstance(data, pd.DataFrame) else data
    clean = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan)
    clean = clean.sort_index()
    clean = clean.loc[~clean.index.duplicated(keep="last")]
    return clean


def consecutive_returns(data: pd.DataFrame | pd.Series) -> pd.Series:
    """Return only observations whose current and previous prices both exist."""

    return (
        _close_series(data).pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).dropna()
    )


def _benchmark_metrics(
    asset_close: pd.Series,
    benchmark: pd.DataFrame | pd.Series | None,
) -> tuple[float | None, float | None]:
    if benchmark is None:
        return None, None
    aligned_prices = pd.concat(
        [asset_close.rename("asset"), _close_series(benchmark).rename("benchmark")], axis=1
    )
    aligned_returns = (
        aligned_prices.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).dropna()
    )
    if len(aligned_returns) < _MINIMUM_RISK_RETURNS:
        return None, None
    benchmark_variance = float(aligned_returns["benchmark"].var(ddof=1))
    if benchmark_variance <= 0:
        return None, None
    covariance = float(aligned_returns.cov().loc["asset", "benchmark"])
    beta = covariance / benchmark_variance
    correlation = float(aligned_returns["asset"].corr(aligned_returns["benchmark"]))
    return _finite(beta), _finite(correlation)


def calculate_risk_metrics(
    history: pd.DataFrame,
    benchmark: pd.DataFrame | pd.Series | None = None,
    *,
    annualisation_days: int = 252,
) -> RiskMetrics:
    if annualisation_days <= 0:
        raise ValueError("annualisation_days debe ser positivo")
    clean = clean_ohlcv(history)
    close = _close_series(history)
    returns = consecutive_returns(history)
    atr_value, _ = calculate_atr_adx(clean)
    atr_pct = (
        _finite(atr_value / float(close.iloc[-1]) * 100.0)
        if atr_value is not None and not close.empty and float(close.iloc[-1]) > 0
        else None
    )
    if len(returns) < _MINIMUM_RISK_RETURNS:
        return RiskMetrics(atr_pct=atr_pct)

    annual_volatility = float(returns.std(ddof=1) * np.sqrt(annualisation_days) * 100.0)
    var_95 = float(max(0.0, -np.quantile(returns, 0.05) * 100.0))
    equity = (1.0 + returns).cumprod()
    max_drawdown = float((equity / equity.cummax() - 1.0).min() * 100.0)
    standard_deviation = float(returns.std(ddof=1))
    sharpe = (
        float(returns.mean() / standard_deviation * np.sqrt(annualisation_days))
        if standard_deviation > 0
        else None
    )
    beta, correlation = _benchmark_metrics(close, benchmark)
    volatility_score = _bounded(100.0 - annual_volatility * 2.0)
    drawdown_score = _bounded(100.0 - abs(max_drawdown) * 2.0)
    tail_risk_score = _bounded(100.0 - var_95 * 20.0)
    sensitivity_score = (
        _bounded(100.0 - max(abs(beta) - 1.0, 0.0) * 35.0) if beta is not None else None
    )
    components = [volatility_score, drawdown_score, tail_risk_score]
    if sensitivity_score is not None:
        components.append(sensitivity_score)
    return RiskMetrics(
        score=_finite(sum(components) / len(components)),
        volatility_score=volatility_score,
        drawdown_score=drawdown_score,
        tail_risk_score=tail_risk_score,
        market_sensitivity_score=sensitivity_score,
        annual_volatility_pct=_finite(annual_volatility),
        var_95_daily_pct=_finite(var_95),
        maximum_drawdown_pct=_finite(max_drawdown),
        beta=beta,
        sharpe_ratio=_finite(sharpe),
        atr_pct=atr_pct,
        benchmark_correlation=correlation,
    )
