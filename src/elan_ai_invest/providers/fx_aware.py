from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from typing import Any

import pandas as pd

from elan_ai_invest.fx import HistoricalFxService, is_fx_asset_id, normalize_fx_pair
from elan_ai_invest.market.quality import assess_market_data_quality

from .base import DownloadResult, MarketDataProvider


def _normalize_index(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result.index = pd.to_datetime(result.index, errors="coerce", utc=True).tz_convert(None)
    result = result.loc[result.index.notna()]
    return result.loc[~result.index.duplicated(keep="last")].sort_index()


class FxAwareMarketDataProvider(MarketDataProvider):
    """Resolve ordinary symbols normally and virtual FX ids through the FX router."""

    def __init__(self, provider: MarketDataProvider, fx_history: HistoricalFxService) -> None:
        self.provider = provider
        self.fx_history = fx_history

    def __getattr__(self, name: str) -> Any:
        return getattr(self.provider, name)

    def download_prices(
        self,
        symbols: Iterable[str],
        period: str,
        interval: str = "1d",
        minimum_history: int = 60,
    ) -> DownloadResult:
        requested = list(
            dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip())
        )
        regular_symbols = [symbol for symbol in requested if not is_fx_asset_id(symbol)]
        fx_symbols = [symbol for symbol in requested if is_fx_asset_id(symbol)]
        frames: list[pd.DataFrame] = []
        errors: dict[str, str] = {}
        sources: dict[str, str] = {}
        route_details: dict[str, dict[str, Any]] = {}
        if regular_symbols:
            regular = self.provider.download_prices(
                regular_symbols,
                period=period,
                interval=interval,
                minimum_history=minimum_history,
            )
            if not regular.prices.empty:
                frames.append(_normalize_index(regular.prices))
            errors.update(regular.errors)
            if regular.quality is not None:
                sources.update(
                    {symbol: quality.source for symbol, quality in regular.quality.assets.items()}
                )

        for symbol in fx_symbols:
            try:
                history = self.fx_history.get_history(
                    normalize_fx_pair(symbol), period=period, interval=interval
                )
                close = pd.to_numeric(history.prices["Close"], errors="coerce").dropna()
                if len(close) < minimum_history:
                    raise ValueError(
                        f"Historico insuficiente: {len(close)} observaciones; minimo {minimum_history}."
                    )
                frames.append(_normalize_index(close.rename(symbol).to_frame()))
                sources[symbol] = f"fx:{history.route.source_type.value.casefold()}"
                route_details[symbol] = {
                    "route_provider": getattr(history.route, "provider", None),
                    "route_path": getattr(history.route, "calculation_path", None),
                    "route_coverage_ratio": float(getattr(history, "coverage_ratio", 1.0)),
                    "received_at": getattr(history, "received_at", None),
                }
            except Exception as exc:
                errors[symbol] = str(exc).strip() or type(exc).__name__

        prices = pd.concat(frames, axis=1).sort_index() if frames else pd.DataFrame()
        quality = assess_market_data_quality(
            prices,
            requested,
            minimum_history=minimum_history,
            provider="Yahoo + FX routing",
            sources=sources,
            errors=errors,
        )
        if route_details:
            assets = dict(quality.assets)
            for symbol, details in route_details.items():
                if symbol in assets:
                    assets[symbol] = replace(assets[symbol], **details)
            quality = replace(quality, assets=assets)
        return DownloadResult(prices=prices, errors=errors, quality=quality)
