from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

import pandas as pd

from elan_ai_invest.market.cache import MarketCache
from elan_ai_invest.market_data import download_market_history

from .history import ProviderHistory, provider_history
from .models import FxPair, ProviderPair

LOGGER = logging.getLogger(__name__)


class YahooFxHistoryProvider:
    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        backoff_seconds: float = 0.5,
        cache: MarketCache | None = None,
        history_loader: Callable[..., pd.DataFrame] = download_market_history,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.cache = cache
        self.history_loader = history_loader

    def load_pair(
        self,
        pair: FxPair,
        *,
        period: str,
        interval: str,
    ) -> ProviderHistory | None:
        provider_pair = ProviderPair(
            provider="Yahoo",
            symbol=f"{pair.base}{pair.quote}=X",
            base=pair.base,
            quote=pair.quote,
        )
        return self.load_provider_pair(provider_pair, period=period, interval=interval)

    def load_provider_pair(
        self,
        pair: ProviderPair,
        *,
        period: str,
        interval: str,
    ) -> ProviderHistory | None:
        if pair.provider.casefold() != "yahoo":
            return None
        try:
            prices = self.history_loader(
                pair.symbol,
                period=period,
                interval=interval,
                timeout_seconds=self.timeout_seconds,
                max_retries=self.max_retries,
                backoff_seconds=self.backoff_seconds,
                cache=self.cache,
            )
        except Exception as exc:
            LOGGER.info(
                "Histórico FX no disponible | provider=Yahoo | symbol=%s | detail=%s",
                pair.symbol,
                str(exc).strip(),
            )
            return None
        return provider_history(pair, prices, received_at=datetime.now(UTC))
