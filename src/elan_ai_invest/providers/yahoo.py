from __future__ import annotations

from typing import Iterable

from elan_ai_invest.market_data import download_adjusted_close
from elan_ai_invest.providers.base import DownloadResult, MarketDataProvider


class YahooMarketDataProvider(MarketDataProvider):
    def download_prices(self, symbols: Iterable[str], period: str) -> DownloadResult:
        return download_adjusted_close(symbols=symbols, period=period)
