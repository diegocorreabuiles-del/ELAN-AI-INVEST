from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .models import TradePlan
from .technical import calculate_atr_adx, clean_ohlcv


def _insufficient(reason: str) -> TradePlan:
    return TradePlan(sufficient_data=False, rationale=(reason,))


def _swing_levels(series: pd.Series, *, radius: int, mode: str) -> list[float]:
    window = radius * 2 + 1
    rolling = series.rolling(window, center=True, min_periods=window)
    reference = rolling.min() if mode == "low" else rolling.max()
    mask = np.isclose(series, reference, rtol=1e-9, atol=1e-12)
    return [float(value) for value in series.loc[mask] if math.isfinite(float(value))]


def _distinct(levels: list[float], *, separation: float) -> list[float]:
    result: list[float] = []
    for level in sorted(levels):
        if not result or level - result[-1] >= separation:
            result.append(level)
    return result


def calculate_trade_plan(
    history: pd.DataFrame,
    *,
    lookback: int = 120,
    swing_radius: int = 3,
    entry_atr_multiple: float = 0.5,
    stop_atr_multiple: float = 0.5,
) -> TradePlan:
    """Build a research-only long plan from observed swings and ATR.

    Risk/reward uses entry_high as the conservative entry reference. No level is
    extrapolated: entries derive from an observed swing low, targets from observed
    swing highs, and ATR is used only to size the entry zone and invalidation buffer.
    """

    if lookback < 28 or swing_radius < 1:
        raise ValueError("lookback y swing_radius no permiten calcular estructura")
    if (
        not math.isfinite(entry_atr_multiple)
        or not math.isfinite(stop_atr_multiple)
        or entry_atr_multiple <= 0
        or stop_atr_multiple <= 0
    ):
        raise ValueError("Los múltiplos ATR deben ser positivos y finitos")
    clean = clean_ohlcv(history).tail(lookback)
    if len(clean) < max(28, swing_radius * 2 + 5):
        return _insufficient("Histórico insuficiente para estructura y ATR.")
    valid_prices = (
        clean[["High", "Low", "Close"]].gt(0).all(axis=1)
        & clean["High"].ge(clean["Low"])
        & clean["Close"].between(clean["Low"], clean["High"])
    )
    if not valid_prices.all():
        return _insufficient("OHLC inválido; no se publican niveles.")

    current_price = float(clean["Close"].iloc[-1])
    atr, _ = calculate_atr_adx(clean)
    if atr is None or not math.isfinite(atr) or atr <= 0:
        return _insufficient("ATR no disponible o no válido.")

    swing_lows = _swing_levels(clean["Low"], radius=swing_radius, mode="low")
    supports = [level for level in swing_lows if 0 < level < current_price]
    if not supports:
        return _insufficient("No existe soporte observado bajo el precio actual.")
    support = max(supports)
    entry_low = support
    entry_high = min(current_price, support + atr * entry_atr_multiple)
    stop = support - atr * stop_atr_multiple
    if stop <= 0 or not stop < entry_low <= entry_high:
        return _insufficient("No existe una invalidación técnica positiva y ordenada.")

    swing_highs = _swing_levels(clean["High"], radius=swing_radius, mode="high")
    overhead = [level for level in swing_highs if level > current_price]
    separation = max(atr * 0.25, current_price * 0.001)
    targets = _distinct(overhead, separation=separation)
    if len(targets) < 2:
        return _insufficient("Se requieren dos resistencias observadas sobre el precio actual.")
    target_1, target_2 = targets[:2]
    risk = entry_high - stop
    if risk <= 0:
        return _insufficient("El riesgo por unidad no es positivo.")

    return TradePlan(
        entry_low=entry_low,
        entry_high=entry_high,
        stop=stop,
        target_1=target_1,
        target_2=target_2,
        risk_reward_1=(target_1 - entry_high) / risk,
        risk_reward_2=(target_2 - entry_high) / risk,
        sufficient_data=True,
        rationale=(
            "Entrada desde soporte observado con zona dimensionada por ATR.",
            "Stop bajo soporte con colchón ATR.",
            "Targets en resistencias observadas; R/R desde el extremo superior de entrada.",
        ),
    )
