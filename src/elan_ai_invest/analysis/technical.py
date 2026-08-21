from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .models import MarketMetrics, TechnicalMetrics

_REQUIRED_OHLC = ("High", "Low", "Close")


def _bounded(value: float) -> float:
    return float(np.clip(value, 0.0, 100.0))


def _finite(value: float | int | np.floating | None) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _weighted_average(values: tuple[tuple[float | None, float], ...]) -> float | None:
    available = [(value, weight) for value, weight in values if value is not None]
    if not available:
        return None
    total_weight = sum(weight for _, weight in available)
    return sum(value * weight for value, weight in available) / total_weight


def clean_ohlcv(history: pd.DataFrame) -> pd.DataFrame:
    missing = set(_REQUIRED_OHLC).difference(history.columns)
    if missing:
        raise ValueError("Faltan columnas OHLC: " + ", ".join(sorted(missing)))
    columns = [*_REQUIRED_OHLC, *(c for c in ("Open", "Volume") if c in history)]
    clean = history.loc[:, columns].copy().sort_index()
    clean = clean.loc[~clean.index.duplicated(keep="last")]
    clean = clean.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    return clean.dropna(subset=list(_REQUIRED_OHLC))


def _period_return(close: pd.Series, sessions: int) -> float | None:
    if len(close) <= sessions:
        return None
    previous = float(close.iloc[-sessions - 1])
    return None if previous <= 0 else (float(close.iloc[-1]) / previous - 1.0) * 100.0


def _year_to_date_return(close: pd.Series) -> float | None:
    if not isinstance(close.index, pd.DatetimeIndex) or close.empty:
        return None
    current_year = close.loc[close.index.year == close.index[-1].year]
    if len(current_year) < 2 or float(current_year.iloc[0]) <= 0:
        return None
    return (float(current_year.iloc[-1]) / float(current_year.iloc[0]) - 1.0) * 100.0


def calculate_market_metrics(history: pd.DataFrame) -> MarketMetrics:
    clean = clean_ohlcv(history)
    if clean.empty:
        return MarketMetrics()
    close = clean["Close"]
    volume = clean.get("Volume")
    current_volume = None
    average_volume = None
    average_dollar_volume = None
    if volume is not None:
        positive_volume = volume.where(volume > 0)
        current_volume = _finite(positive_volume.iloc[-1])
        if len(positive_volume) >= 20 and positive_volume.tail(20).notna().all():
            average_volume = _finite(positive_volume.tail(20).mean())
            average_dollar_volume = _finite((close * positive_volume).tail(20).mean())
    return MarketMetrics(
        price=_finite(close.iloc[-1]),
        change_1d_pct=_finite(_period_return(close, 1)),
        change_7d_pct=_finite(_period_return(close, 5)),
        change_30d_pct=_finite(_period_return(close, 21)),
        change_ytd_pct=_finite(_year_to_date_return(close)),
        change_1y_pct=_finite(_period_return(close, 252)),
        volume=current_volume,
        average_volume_20d=average_volume,
        average_dollar_volume=average_dollar_volume,
    )


def _rsi(close: pd.Series, window: int = 14) -> float | None:
    if len(close) < window + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    last_gain = _finite(gain.iloc[-1])
    last_loss = _finite(loss.iloc[-1])
    if last_gain is None or last_loss is None:
        return None
    if last_loss == 0:
        return 100.0 if last_gain > 0 else 50.0
    return 100.0 - 100.0 / (1.0 + last_gain / last_loss)


def _macd(close: pd.Series) -> tuple[float | None, float | None]:
    if len(close) < 35:
        return None, None
    line = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal = line.ewm(span=9, adjust=False).mean()
    return _finite(line.iloc[-1]), _finite(signal.iloc[-1])


def calculate_atr_adx(history: pd.DataFrame, window: int = 14) -> tuple[float | None, float | None]:
    if len(history) < window * 2:
        return None, None
    high, low, close = history["High"], history["Low"], history["Close"]
    true_range = pd.concat(
        [(high - low).abs(), (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    atr = true_range.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    up_move, down_move = high.diff(), -low.diff()
    positive_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    negative_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    denominator = atr.replace(0.0, np.nan)
    positive_di = (
        100.0
        * positive_dm.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
        / denominator
    )
    negative_di = (
        100.0
        * negative_dm.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
        / denominator
    )
    dx = (
        100.0 * (positive_di - negative_di).abs() / (positive_di + negative_di).replace(0.0, np.nan)
    )
    adx = dx.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    return _finite(atr.iloc[-1]), _finite(adx.iloc[-1])


def _trend_score(
    price: float,
    sma_50: float | None,
    sma_200: float | None,
    ema_20: float | None,
    ema_50: float | None,
) -> float | None:
    comparisons: list[bool] = []
    if sma_50 is not None:
        comparisons.append(price > sma_50)
    if sma_200 is not None:
        comparisons.append(price > sma_200)
    if sma_50 is not None and sma_200 is not None:
        comparisons.append(sma_50 > sma_200)
    if ema_20 is not None and ema_50 is not None:
        comparisons.append(ema_20 > ema_50)
    return 100.0 * sum(comparisons) / len(comparisons) if comparisons else None


def _momentum_score(
    rsi: float | None,
    macd: float | None,
    macd_signal: float | None,
    return_1m: float | None,
    return_3m: float | None,
) -> float | None:
    components: list[float] = []
    if rsi is not None:
        components.append(_bounded(100.0 - abs(rsi - 60.0) * 2.5))
    if macd is not None and macd_signal is not None:
        components.append(75.0 if macd > macd_signal else 25.0)
    if return_1m is not None:
        components.append(_bounded(50.0 + return_1m * 2.0))
    if return_3m is not None:
        components.append(_bounded(50.0 + return_3m))
    return sum(components) / len(components) if components else None


def calculate_technical_metrics(history: pd.DataFrame) -> TechnicalMetrics:
    clean = clean_ohlcv(history)
    if len(clean) < 20:
        return TechnicalMetrics()
    close = clean["Close"]
    price = float(close.iloc[-1])
    sma_50 = _finite(close.rolling(50, min_periods=50).mean().iloc[-1])
    sma_200 = _finite(close.rolling(200, min_periods=200).mean().iloc[-1])
    ema_20 = _finite(close.ewm(span=20, adjust=False, min_periods=20).mean().iloc[-1])
    ema_50 = _finite(close.ewm(span=50, adjust=False, min_periods=50).mean().iloc[-1])
    ema_200 = _finite(close.ewm(span=200, adjust=False, min_periods=200).mean().iloc[-1])
    rsi = _rsi(close)
    macd, macd_signal = _macd(close)
    atr, adx = calculate_atr_adx(clean)
    returns = close.pct_change(fill_method=None).dropna()
    annual_volatility = (
        _finite(returns.tail(63).std(ddof=1) * np.sqrt(252) * 100) if len(returns) >= 20 else None
    )
    volume = clean.get("Volume")
    rvol = None
    if volume is not None and len(volume) >= 21 and volume.iloc[-21:-1].gt(0).all():
        average_volume = float(volume.iloc[-21:-1].mean())
        rvol = _finite(float(volume.iloc[-1]) / average_volume) if average_volume > 0 else None
    window_52w = clean.tail(252)
    high_52w = _finite(window_52w["High"].max()) if len(window_52w) >= 50 else None
    low_52w = _finite(window_52w["Low"].min()) if len(window_52w) >= 50 else None
    structure_window = clean.tail(60)
    support = _finite(structure_window["Low"].min())
    resistance = _finite(structure_window["High"].max())
    trend_score = _trend_score(price, sma_50, sma_200, ema_20, ema_50)
    momentum_score = _momentum_score(
        rsi, macd, macd_signal, _period_return(close, 21), _period_return(close, 63)
    )
    volume_score = _bounded(50.0 + (rvol - 1.0) * 35.0) if rvol is not None else None
    volatility_score = (
        _bounded(100.0 - annual_volatility * 2.0) if annual_volatility is not None else None
    )
    structure_score = None
    if high_52w is not None and low_52w is not None and high_52w > low_52w:
        structure_score = _bounded((price - low_52w) / (high_52w - low_52w) * 100.0)
    score = _weighted_average(
        (
            (trend_score, 0.35),
            (momentum_score, 0.25),
            (volume_score, 0.15),
            (volatility_score, 0.10),
            (structure_score, 0.15),
        )
    )
    return TechnicalMetrics(
        score=_finite(score),
        trend_score=_finite(trend_score),
        momentum_score=_finite(momentum_score),
        volume_score=_finite(volume_score),
        volatility_score=_finite(volatility_score),
        structure_score=_finite(structure_score),
        sma_50=sma_50,
        sma_200=sma_200,
        ema_20=ema_20,
        ema_50=ema_50,
        ema_200=ema_200,
        rsi_14=_finite(rsi),
        macd=macd,
        macd_signal=macd_signal,
        adx_14=adx,
        atr_14=atr,
        rvol_20=rvol,
        distance_to_high_52w_pct=(
            _finite((price / high_52w - 1.0) * 100.0) if high_52w and high_52w > 0 else None
        ),
        distance_to_low_52w_pct=(
            _finite((price / low_52w - 1.0) * 100.0) if low_52w and low_52w > 0 else None
        ),
        support=support,
        resistance=resistance,
        price_vs_sma_50_pct=(
            _finite((price / sma_50 - 1.0) * 100.0) if sma_50 and sma_50 > 0 else None
        ),
        price_vs_sma_200_pct=(
            _finite((price / sma_200 - 1.0) * 100.0) if sma_200 and sma_200 > 0 else None
        ),
    )
