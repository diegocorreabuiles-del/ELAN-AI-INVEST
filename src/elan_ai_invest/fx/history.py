from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

import numpy as np
import pandas as pd

from .models import FxHistory, FxPair, FxRoute, FxSourceType, ProviderPair
from .registry import CurrencyRegistry
from .routing import FxRoutingEngine, route_from_provider_pair

OHLC_COLUMNS = ("Open", "High", "Low", "Close")


@dataclass(frozen=True)
class ProviderHistory:
    provider_pair: ProviderPair
    prices: pd.DataFrame
    received_at: datetime


class FxHistoryProvider(Protocol):
    def load_pair(
        self,
        pair: FxPair,
        *,
        period: str,
        interval: str,
    ) -> ProviderHistory | None: ...

    def load_provider_pair(
        self,
        pair: ProviderPair,
        *,
        period: str,
        interval: str,
    ) -> ProviderHistory | None: ...


def sanitize_fx_history(frame: pd.DataFrame) -> pd.DataFrame:
    missing = set(OHLC_COLUMNS).difference(frame.columns)
    if missing:
        raise ValueError("Faltan columnas OHLC FX: " + ", ".join(sorted(missing)))
    result = frame.copy()
    index = pd.to_datetime(result.index, errors="coerce", utc=True)
    result.index = index
    result = result.loc[result.index.notna()].sort_index()
    result = result.loc[~result.index.duplicated(keep="last")]
    for column in OHLC_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")
        result[column] = result[column].replace([np.inf, -np.inf], np.nan)
        result[column] = result[column].where(result[column] > 0)
    result = result.dropna(subset=list(OHLC_COLUMNS))
    coherent = result["High"].ge(result[["Open", "Close"]].max(axis=1)) & result["Low"].le(
        result[["Open", "Close"]].min(axis=1)
    )
    result = result.loc[coherent]
    if result.empty:
        raise ValueError("El histórico FX no contiene observaciones OHLC válidas.")
    if "Volume" not in result:
        result["Volume"] = 0.0
    result["Volume"] = pd.to_numeric(result["Volume"], errors="coerce").fillna(0.0)
    return result


def invert_fx_history(frame: pd.DataFrame) -> pd.DataFrame:
    source = sanitize_fx_history(frame)
    inverted = pd.DataFrame(index=source.index)
    inverted["Open"] = 1.0 / source["Open"]
    inverted["High"] = 1.0 / source["Low"]
    inverted["Low"] = 1.0 / source["High"]
    inverted["Close"] = 1.0 / source["Close"]
    inverted["Volume"] = 0.0
    return sanitize_fx_history(inverted)


def multiply_fx_histories(frames: list[pd.DataFrame]) -> tuple[pd.DataFrame, float]:
    if not frames:
        raise ValueError("Se necesita al menos un histórico para construir el cruce.")
    sanitized = [sanitize_fx_history(frame) for frame in frames]
    common_index = sanitized[0].index
    union_index = sanitized[0].index
    for frame in sanitized[1:]:
        common_index = common_index.intersection(frame.index)
        union_index = union_index.union(frame.index)
    common_index = common_index.sort_values()
    if len(common_index) < 2:
        raise ValueError("No hay suficientes fechas comunes para construir el cruce FX.")
    result = pd.DataFrame(index=common_index)
    for column in OHLC_COLUMNS:
        values = pd.Series(1.0, index=common_index)
        for frame in sanitized:
            values = values.mul(frame.loc[common_index, column])
        result[column] = values
    result["Volume"] = 0.0
    coverage = len(common_index) / len(union_index) if len(union_index) else 0.0
    return sanitize_fx_history(result), float(coverage)


class HistoricalFxService:
    def __init__(
        self,
        registry: CurrencyRegistry,
        provider: FxHistoryProvider,
        routing: FxRoutingEngine | None = None,
    ) -> None:
        self.registry = registry
        self.provider = provider
        self.routing = routing or FxRoutingEngine(registry)

    def get_history(
        self,
        pair: FxPair,
        *,
        period: str = "2y",
        interval: str = "1d",
    ) -> FxHistory:
        self.registry.validate_pair(pair)
        direct = self.provider.load_pair(pair, period=period, interval=interval)
        if direct is not None:
            route = route_from_provider_pair(pair, direct.provider_pair, inverted=False)
            return self._single_history(pair, direct, route, inverted=False)

        inverse = self.provider.load_pair(pair.inverse(), period=period, interval=interval)
        if inverse is not None:
            route = route_from_provider_pair(pair, inverse.provider_pair, inverted=True)
            return self._single_history(pair, inverse, route, inverted=True)

        attempted: set[str] = set()
        for route in self.routing.find_routes(pair):
            if len(route.legs) == 1:
                leg = route.legs[0]
                history = self.provider.load_provider_pair(
                    leg.provider_pair,
                    period=period,
                    interval=interval,
                )
                attempted.add(f"{leg.provider_pair.provider}:{leg.provider_pair.symbol}")
                if history is not None:
                    return self._single_history(
                        pair,
                        history,
                        route,
                        inverted=leg.inverted,
                    )
                continue
            loaded: list[ProviderHistory] = []
            transformed: list[pd.DataFrame] = []
            failed = False
            for leg in route.legs:
                key = f"{leg.provider_pair.provider}:{leg.provider_pair.symbol}"
                history = self.provider.load_provider_pair(
                    leg.provider_pair,
                    period=period,
                    interval=interval,
                )
                attempted.add(key)
                if history is None:
                    failed = True
                    break
                loaded.append(history)
                transformed.append(
                    invert_fx_history(history.prices)
                    if leg.inverted
                    else sanitize_fx_history(history.prices)
                )
            if failed:
                continue
            prices, coverage = multiply_fx_histories(transformed)
            synthetic_route = FxRoute(pair, FxSourceType.SYNTHETIC, route.legs)
            return FxHistory(
                pair=pair,
                prices=prices,
                route=synthetic_route,
                coverage_ratio=coverage,
                market_timestamp=prices.index[-1],
                received_at=max(item.received_at for item in loaded),
            )
        detail = f"; rutas intentadas: {', '.join(sorted(attempted))}" if attempted else ""
        raise ValueError(f"No hay histórico FX fiable para {pair.display}{detail}.")

    @staticmethod
    def _single_history(
        pair: FxPair,
        history: ProviderHistory,
        route: FxRoute,
        *,
        inverted: bool,
    ) -> FxHistory:
        prices = (
            invert_fx_history(history.prices) if inverted else sanitize_fx_history(history.prices)
        )
        return FxHistory(
            pair=pair,
            prices=prices,
            route=route,
            coverage_ratio=1.0,
            market_timestamp=prices.index[-1],
            received_at=history.received_at,
        )


def provider_history(
    pair: ProviderPair,
    prices: pd.DataFrame,
    *,
    received_at: datetime | None = None,
) -> ProviderHistory:
    return ProviderHistory(
        provider_pair=pair,
        prices=sanitize_fx_history(prices),
        received_at=received_at or datetime.now(UTC),
    )
