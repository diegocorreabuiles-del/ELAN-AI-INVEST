from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CorrelationStatistics:
    correlation: float | None
    observations: int
    coverage_ratio: float
    start_date: pd.Timestamp | None
    end_date: pd.Timestamp | None


@dataclass(frozen=True)
class CorrelationMatrixResult:
    correlation: pd.DataFrame
    observations: pd.DataFrame
    coverage: pd.DataFrame


@dataclass(frozen=True)
class FxKpis:
    latest: float
    change_1d_pct: float | None
    change_7d_pct: float | None
    change_30d_pct: float | None
    ytd_pct: float | None
    change_1y_pct: float | None
    volatility_30d_pct: float | None
    volatility_1y_pct: float | None
    high_52w: float | None
    low_52w: float | None
    distance_to_high_52w_pct: float | None
    distance_to_low_52w_pct: float | None
    sma_50: float | None
    sma_200: float | None
    rsi_14: float | None
    atr_14: float | None
    trend: str


CORRELATION_PERIODS = {
    "30D": 30,
    "90D": 90,
    "180D": 180,
    "1Y": 252,
    "3Y": 756,
    "5Y": 1260,
}
ROLLING_WINDOWS = (20, 60, 120, 252)


def _positive_series(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    values = values.replace([np.inf, -np.inf], np.nan).where(values > 0)
    values.index = pd.to_datetime(values.index, errors="coerce", utc=True)
    values = values.loc[values.index.notna()].sort_index()
    return values.loc[~values.index.duplicated(keep="last")]


def log_returns(series: pd.Series) -> pd.Series:
    prices = _positive_series(series).dropna()
    returns = np.log(prices / prices.shift(1))
    return returns.replace([np.inf, -np.inf], np.nan).dropna()


def correlation_statistics(
    first: pd.Series,
    second: pd.Series,
    *,
    lookback_sessions: int | None = None,
) -> CorrelationStatistics:
    if lookback_sessions is not None and lookback_sessions < 2:
        raise ValueError("El periodo de correlación debe tener al menos 2 sesiones.")
    first_clean = _positive_series(first).dropna().rename("first")
    second_clean = _positive_series(second).dropna().rename("second")
    union_index = first_clean.index.union(second_clean.index)
    aligned = pd.concat([first_clean, second_clean], axis=1, join="inner").dropna()
    if lookback_sessions is not None:
        aligned = aligned.tail(lookback_sessions + 1)
        if len(union_index):
            cutoff = aligned.index.min() if not aligned.empty else union_index.max()
            union_index = union_index[union_index >= cutoff]
    coverage = len(aligned) / len(union_index) if len(union_index) else 0.0
    returns = np.log(aligned / aligned.shift(1)).replace([np.inf, -np.inf], np.nan).dropna()
    correlation: float | None = None
    if len(returns) >= 2:
        value = float(returns["first"].corr(returns["second"]))
        correlation = value if np.isfinite(value) else None
    return CorrelationStatistics(
        correlation=correlation,
        observations=len(returns),
        coverage_ratio=float(coverage),
        start_date=returns.index.min() if not returns.empty else None,
        end_date=returns.index.max() if not returns.empty else None,
    )


def rolling_correlation(
    first: pd.Series,
    second: pd.Series,
    *,
    window: int = 60,
) -> pd.Series:
    if window < 2:
        raise ValueError("La ventana móvil debe tener al menos 2 sesiones.")
    aligned = pd.concat(
        [_positive_series(first).rename("first"), _positive_series(second).rename("second")],
        axis=1,
        join="inner",
    ).dropna()
    returns = np.log(aligned / aligned.shift(1)).replace([np.inf, -np.inf], np.nan).dropna()
    minimum_periods = min(20, window)
    result = returns["first"].rolling(window, min_periods=minimum_periods).corr(returns["second"])
    result = result.replace([np.inf, -np.inf], np.nan).dropna()
    result.name = "Correlación"
    return result


def correlation_matrix(
    prices: pd.DataFrame,
    *,
    lookback_sessions: int | None = None,
) -> CorrelationMatrixResult:
    columns = list(dict.fromkeys(str(column) for column in prices.columns))
    correlation = pd.DataFrame(np.nan, index=columns, columns=columns, dtype=float)
    observations = pd.DataFrame(0, index=columns, columns=columns, dtype=int)
    coverage = pd.DataFrame(0.0, index=columns, columns=columns, dtype=float)
    for index, first in enumerate(columns):
        for second in columns[index:]:
            stats = correlation_statistics(
                prices[first],
                prices[second],
                lookback_sessions=lookback_sessions,
            )
            value = stats.correlation
            if first == second and stats.observations:
                value = 1.0
            correlation.loc[first, second] = value
            correlation.loc[second, first] = value
            observations.loc[first, second] = stats.observations
            observations.loc[second, first] = stats.observations
            coverage.loc[first, second] = stats.coverage_ratio
            coverage.loc[second, first] = stats.coverage_ratio
    return CorrelationMatrixResult(correlation, observations, coverage)


def _period_change(close: pd.Series, sessions: int) -> float | None:
    if len(close) <= sessions:
        return None
    value = (float(close.iloc[-1]) / float(close.iloc[-sessions - 1]) - 1.0) * 100.0
    return value if np.isfinite(value) else None


def _annualized_volatility(close: pd.Series, sessions: int) -> float | None:
    sample = close.tail(sessions + 1)
    returns = log_returns(sample)
    if len(returns) < 2:
        return None
    value = float(returns.std(ddof=1) * np.sqrt(252) * 100.0)
    return value if np.isfinite(value) else None


def _rsi(close: pd.Series, window: int = 14) -> float | None:
    changes = close.diff().dropna().tail(window)
    if len(changes) < window:
        return None
    gains = changes.clip(lower=0).mean()
    losses = -changes.clip(upper=0).mean()
    if losses == 0:
        return 100.0 if gains > 0 else 50.0
    value = float(100.0 - (100.0 / (1.0 + gains / losses)))
    return value if np.isfinite(value) else None


def _atr(history: pd.DataFrame, window: int = 14) -> float | None:
    if len(history) < window + 1:
        return None
    previous_close = history["Close"].shift(1)
    true_range = pd.concat(
        [
            history["High"] - history["Low"],
            (history["High"] - previous_close).abs(),
            (history["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    value = float(true_range.tail(window).mean())
    return value if np.isfinite(value) else None


def compute_fx_kpis(history: pd.DataFrame) -> FxKpis:
    required = {"High", "Low", "Close"}
    missing = required.difference(history.columns)
    if missing:
        raise ValueError("Faltan columnas para los KPIs FX: " + ", ".join(sorted(missing)))
    working = history.copy()
    working.index = pd.to_datetime(working.index, errors="coerce", utc=True)
    working = working.loc[working.index.notna()].sort_index()
    working = working.loc[~working.index.duplicated(keep="last")]
    for column in required:
        values = pd.to_numeric(working[column], errors="coerce")
        working[column] = values.replace([np.inf, -np.inf], np.nan).where(values > 0)
    working = working.dropna(subset=list(required))
    if working.empty:
        raise ValueError("No hay histórico válido para calcular KPIs FX.")
    close = working["Close"]
    latest = float(close.iloc[-1])
    year = close.index[-1].year
    ytd = close.loc[close.index.year == year]
    ytd_change = (latest / float(ytd.iloc[0]) - 1.0) * 100.0 if len(ytd) >= 2 else None
    trailing = working.tail(252)
    high_52w = float(trailing["High"].max()) if not trailing.empty else None
    low_52w = float(trailing["Low"].min()) if not trailing.empty else None
    sma_50 = float(close.tail(50).mean()) if len(close) >= 50 else None
    sma_200 = float(close.tail(200).mean()) if len(close) >= 200 else None
    if sma_50 is not None and sma_200 is not None:
        trend = (
            "Alcista"
            if latest > sma_50 > sma_200
            else "Bajista" if latest < sma_50 < sma_200 else "Mixta"
        )
    elif sma_50 is not None:
        trend = "Alcista" if latest > sma_50 else "Bajista"
    else:
        trend = "N/D"
    return FxKpis(
        latest=latest,
        change_1d_pct=_period_change(close, 1),
        change_7d_pct=_period_change(close, 7),
        change_30d_pct=_period_change(close, 30),
        ytd_pct=ytd_change,
        change_1y_pct=_period_change(close, 252),
        volatility_30d_pct=_annualized_volatility(close, 30),
        volatility_1y_pct=_annualized_volatility(close, 252),
        high_52w=high_52w,
        low_52w=low_52w,
        distance_to_high_52w_pct=(latest / high_52w - 1.0) * 100.0 if high_52w else None,
        distance_to_low_52w_pct=(latest / low_52w - 1.0) * 100.0 if low_52w else None,
        sma_50=sma_50,
        sma_200=sma_200,
        rsi_14=_rsi(close),
        atr_14=_atr(working),
        trend=trend,
    )
