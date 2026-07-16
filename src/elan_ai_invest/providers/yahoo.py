from __future__ import annotations

from collections.abc import Iterable

from elan_ai_invest.market_data import download_adjusted_close
from elan_ai_invest.providers.base import DownloadResult, MarketDataProvider


class YahooMarketDataProvider(MarketDataProvider):
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
        )
