from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import pandas as pd


class MarketCache:
    """Disk cache that stores market data as inert CSV instead of pickle."""

    def __init__(
        self,
        cache_dir: str | Path = "data/cache",
        ttl_seconds: float = 3600,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if ttl_seconds < 0:
            raise ValueError("El TTL de caché no puede ser negativo")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = float(ttl_seconds)
        self._clock = clock

    @staticmethod
    def _key(symbol: str, period: str, interval: str) -> str:
        payload = json.dumps(
            {"symbol": symbol.upper(), "period": period, "interval": interval},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _path(self, symbol: str, period: str, interval: str) -> Path:
        return self.cache_dir / f"{self._key(symbol, period, interval)}.csv"

    def save(
        self,
        symbol: str,
        data: pd.DataFrame,
        period: str = "2y",
        interval: str = "1d",
    ) -> None:
        if data.empty:
            return
        destination = self._path(symbol, period, interval)
        temporary = destination.with_suffix(f".{uuid4().hex}.tmp")
        try:
            data.to_csv(temporary, index=True)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    def load(
        self,
        symbol: str,
        period: str = "2y",
        interval: str = "1d",
    ) -> pd.DataFrame | None:
        path = self._path(symbol, period, interval)
        if not path.exists() or self.ttl_seconds == 0:
            return None
        age_seconds = max(0.0, self._clock() - path.stat().st_mtime)
        if age_seconds > self.ttl_seconds:
            return None
        try:
            frame = pd.read_csv(path, index_col=0, parse_dates=True)
        except (OSError, ValueError, pd.errors.ParserError):
            return None
        return None if frame.empty else frame
