from __future__ import annotations

import time
from collections.abc import Callable, Iterable

import pandas as pd

from elan_ai_invest.market.cache import MarketCache
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

    raise ValueError("no se encontró la columna de cierre")


def _load_yfinance_downloader() -> Callable[..., pd.DataFrame]:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError(
            "Falta yfinance. Ejecuta update.bat antes de descargar mercado."
        ) from exc
    return yf.download


def _extract_history(frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if frame.empty:
        raise ValueError("sin datos")

    fields = ("Open", "High", "Low", "Close", "Volume")
    history: dict[str, pd.Series] = {}
    if isinstance(frame.columns, pd.MultiIndex):
        first_level = frame.columns.get_level_values(0)
        second_level = frame.columns.get_level_values(1)
        if any(field in first_level for field in fields):
            for field in fields:
                if field not in first_level:
                    continue
                values = frame[field]
                if isinstance(values, pd.DataFrame):
                    values = values[symbol] if symbol in values.columns else values.iloc[:, 0]
                history[field] = values
        elif any(field in second_level for field in fields):
            for field in fields:
                if field not in second_level:
                    continue
                values = frame.xs(field, axis=1, level=1)
                if isinstance(values, pd.DataFrame):
                    values = values[symbol] if symbol in values.columns else values.iloc[:, 0]
                history[field] = values
    else:
        history = {field: frame[field] for field in fields if field in frame.columns}

    required = {"Open", "High", "Low", "Close"}
    missing = required.difference(history)
    if missing:
        raise ValueError("faltan columnas OHLC: " + ", ".join(sorted(missing)))

    result = pd.DataFrame(history).sort_index()
    result = result.loc[~result.index.duplicated(keep="last")]
    result = result.dropna(subset=list(required))
    if "Volume" not in result:
        result["Volume"] = 0.0
    result["Volume"] = pd.to_numeric(result["Volume"], errors="coerce").fillna(0.0)
    return result


def download_market_history(
    symbol: str,
    period: str = "2y",
    interval: str = "1d",
    *,
    timeout_seconds: float = 10.0,
    max_retries: int = 2,
    backoff_seconds: float = 0.5,
    downloader: Callable[..., pd.DataFrame] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> pd.DataFrame:
    normalized_symbol = str(symbol).strip().upper()
    if not normalized_symbol:
        raise ValueError("El símbolo no puede estar vacío")
    if timeout_seconds <= 0:
        raise ValueError("El timeout de mercado debe ser positivo")
    if max_retries < 0:
        raise ValueError("Los reintentos de mercado no pueden ser negativos")
    if backoff_seconds < 0:
        raise ValueError("El backoff de mercado no puede ser negativo")

    download = downloader or _load_yfinance_downloader()
    attempts = max_retries + 1
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            frame = download(
                normalized_symbol,
                period=period,
                interval=interval,
                auto_adjust=True,
                actions=False,
                progress=False,
                threads=False,
                timeout=timeout_seconds,
            )
            if frame is None:
                raise ValueError("sin datos")
            history = _extract_history(frame, normalized_symbol)
            if len(history) < 2:
                raise ValueError("historial insuficiente: menos de 2 sesiones")
            return history
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                sleep(backoff_seconds * (2**attempt))

    detail = str(last_error).strip() if last_error is not None else "error desconocido"
    raise RuntimeError(
        f"descarga OHLCV fallida para {normalized_symbol} tras {attempts} intentos: {detail}"
    ) from last_error


def _cached_close(
    cache: MarketCache | None,
    symbol: str,
    period: str,
    interval: str,
    minimum_history: int,
) -> pd.Series | None:
    if cache is None:
        return None
    cached = cache.load(symbol, period, interval)
    if cached is None:
        return None
    try:
        close = _extract_close(cached, symbol).rename(symbol).dropna()
    except ValueError:
        return None
    return close if len(close) >= minimum_history else None


def download_adjusted_close(
    symbols: Iterable[str],
    period: str = "2y",
    interval: str = "1d",
    minimum_history: int = 60,
    *,
    timeout_seconds: float = 10.0,
    max_retries: int = 2,
    backoff_seconds: float = 0.5,
    cache: MarketCache | None = None,
    downloader: Callable[..., pd.DataFrame] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> DownloadResult:
    if timeout_seconds <= 0:
        raise ValueError("El timeout de mercado debe ser positivo")
    if max_retries < 0:
        raise ValueError("Los reintentos de mercado no pueden ser negativos")
    if backoff_seconds < 0:
        raise ValueError("El backoff de mercado no puede ser negativo")

    download = downloader or _load_yfinance_downloader()
    series: list[pd.Series] = []
    errors: dict[str, str] = {}

    for raw_symbol in symbols:
        symbol = str(raw_symbol).strip().upper()
        if not symbol:
            continue

        close = _cached_close(cache, symbol, period, interval, minimum_history)
        if close is not None:
            series.append(close)
            continue

        frame: pd.DataFrame | None = None
        last_error: Exception | None = None
        attempts = max_retries + 1
        for attempt in range(attempts):
            try:
                frame = download(
                    symbol,
                    period=period,
                    interval=interval,
                    auto_adjust=True,
                    progress=False,
                    threads=False,
                    timeout=timeout_seconds,
                )
                if frame is None or frame.empty:
                    raise ValueError("sin datos")
                break
            except Exception as exc:
                last_error = exc
                frame = None
                if attempt < max_retries:
                    sleep(backoff_seconds * (2**attempt))

        if frame is None:
            detail = str(last_error).strip() if last_error is not None else "error desconocido"
            errors[symbol] = f"descarga fallida tras {attempts} intentos: {detail}"
            continue

        try:
            close = _extract_close(frame, symbol).rename(symbol).dropna()
            if len(close) < minimum_history:
                raise ValueError(
                    f"historial insuficiente: {len(close)} < {minimum_history} sesiones"
                )
            series.append(close)
            if cache is not None:
                cache.save(symbol, close.rename("Close").to_frame(), period, interval)
        except Exception as exc:
            errors[symbol] = str(exc)

    prices = pd.concat(series, axis=1).sort_index() if series else pd.DataFrame()
    return DownloadResult(prices=prices, errors=errors)
