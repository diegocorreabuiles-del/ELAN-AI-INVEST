from __future__ import annotations

from pathlib import Path

from elan_ai_invest.core.config import load_settings
from elan_ai_invest.core.engine import CoreEngine
from elan_ai_invest.core.logging import configure_logging
from elan_ai_invest.fx import HistoricalFxService, YahooFxHistoryProvider, load_currency_registry
from elan_ai_invest.market.cache import MarketCache
from elan_ai_invest.providers.base import MarketDataProvider
from elan_ai_invest.providers.fx_aware import FxAwareMarketDataProvider
from elan_ai_invest.providers.yahoo import YahooMarketDataProvider


def build_core_engine(root: Path) -> CoreEngine:
    settings = load_settings(root / "config" / "settings.yaml")
    logger = configure_logging(settings.logging, root)

    cache = MarketCache(
        root / settings.market.cache_directory,
        ttl_seconds=settings.market.cache_ttl_seconds,
    )
    providers = {
        "yahoo": lambda: YahooMarketDataProvider(
            timeout_seconds=settings.market.timeout_seconds,
            max_retries=settings.market.max_retries,
            backoff_seconds=settings.market.backoff_seconds,
            cache=cache,
        ),
    }
    provider_factory = providers.get(settings.market.provider.lower())
    if provider_factory is None:
        raise ValueError(f"Proveedor no soportado: {settings.market.provider}")

    provider: MarketDataProvider = provider_factory()
    currency_registry_path = root / "config" / "currencies.csv"
    if currency_registry_path.is_file():
        fx_provider = YahooFxHistoryProvider(
            timeout_seconds=settings.market.timeout_seconds,
            max_retries=settings.market.max_retries,
            backoff_seconds=settings.market.backoff_seconds,
            cache=cache,
        )
        provider = FxAwareMarketDataProvider(
            provider,
            HistoricalFxService(
                load_currency_registry(currency_registry_path),
                fx_provider,
            ),
        )

    return CoreEngine(
        settings=settings,
        provider=provider,
        root=root,
        logger=logger,
    )
