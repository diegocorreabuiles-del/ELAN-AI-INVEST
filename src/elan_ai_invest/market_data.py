from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import yfinance as yf


@dataclass(frozen=True)
class MarketDataResult:
    prices: pd.DataFrame
    errors: dict[str, str]


def download_adjusted_close(symbols: Iterable[str], period: str = "2y") -> MarketDataResult:
    series: list[pd.Series] = []
    errors: dict[str, str] = {}

    for symbol in symbols:
        try:
            frame = yf.download(symbol, period=period, auto_adjust=True, progress=False)
            if frame.empty:
                errors[symbol] = "No se recibieron datos."
                continue

            close = frame["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            close = close.rename(symbol).dropna()
            if close.empty:
                errors[symbol] = "La serie de cierre esta vacia."
                continue
            series.append(close)
        except Exception as exc:  # noqa: BLE001
            errors[symbol] = str(exc)

    prices = pd.concat(series, axis=1).sort_index() if series else pd.DataFrame()
    return MarketDataResult(prices=prices, errors=errors)
