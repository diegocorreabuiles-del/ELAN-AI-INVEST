from __future__ import annotations

from pathlib import Path

from elan_ai_invest.core.config import load_settings
from elan_ai_invest.core.engine import CoreEngine
from elan_ai_invest.core.logging import configure_logging
from elan_ai_invest.providers.yahoo import YahooMarketDataProvider


def build_core_engine(root: Path) -> CoreEngine:
    settings = load_settings(root / "config" / "settings.yaml")
    logger = configure_logging(settings.logging, root)

    providers = {
        "yahoo": YahooMarketDataProvider,
    }
    provider_cls = providers.get(settings.market.provider.lower())
    if provider_cls is None:
        raise ValueError(f"Proveedor no soportado: {settings.market.provider}")

    return CoreEngine(
        settings=settings,
        provider=provider_cls(),
        root=root,
        logger=logger,
    )
