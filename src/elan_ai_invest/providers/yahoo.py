from __future__ import annotations

from collections.abc import Iterable

from elan_ai_invest.market.cache import MarketCache
from elan_ai_invest.market_data import download_adjusted_close
from elan_ai_invest.providers.base import DownloadResult, MarketDataProvider


class YahooMarketDataProvider(MarketDataProvider):
    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        backoff_seconds: float = 0.5,
        cache: MarketCache | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.cache = cache

    def download_prices(
        self,
        symbols: Iterable[str],
        period: str,
        interval: str = "1d",
        minimum_history: int = 60,
    ) -> DownloadResult:
        return download_adjusted_close(
            symbols=symbols,
            period=period,
            interval=interval,
            minimum_history=minimum_history,
            timeout_seconds=self.timeout_seconds,
            max_retries=self.max_retries,
            backoff_seconds=self.backoff_seconds,
            cache=self.cache,
        )
