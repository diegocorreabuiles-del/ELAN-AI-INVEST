from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
import yfinance as yf

from elan_ai_invest.providers.base import DownloadResult


def _extract_close(frame: pd.DataFrame, symbol: str) -> pd.Series:
    if frame.empty:
        raise ValueError("sin datos")
    if isinstance(frame.columns, pd.MultiIndex):
        for field in ("Adj Close", "Close"):
            if field in frame.columns.get_level_values(0):
                data = frame[field]
                if isinstance(data, pd.DataFrame):
                    if symbol in data.columns:
                        return data[symbol]
                    return data.iloc[:, 0]
    for field in ("Adj Close", "Close"):
        if field in frame.columns:
            return frame[field]
    raise ValueError("no se encontro la columna de cierre")


def download_adjusted_close(symbols: Iterable[str], period: str = "2y") -> DownloadResult:
    series: list[pd.Series] = []
    errors: dict[str, str] = {}
    for symbol in symbols:
        try:
            frame = yf.download(
                symbol,
                period=period,
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            close = _extract_close(frame, symbol).rename(symbol).dropna()
            if len(close) < 60:
                raise ValueError("historial insuficiente")
            series.append(close)
        except Exception as exc:  # provider/network errors are shown in the UI
            errors[symbol] = str(exc)
    prices = pd.concat(series, axis=1).sort_index() if series else pd.DataFrame()
    return DownloadResult(prices=prices, errors=errors)
