from __future__ import annotations

import math
from collections import deque

from .models import FxPair, FxRoute, FxRouteLeg, FxSourceType, ProviderPair
from .registry import CurrencyRegistry


def invert_fx_rate(rate: float) -> float:
    value = float(rate)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("La cotización que se va a invertir debe ser positiva y finita.")
    return 1.0 / value


def calculate_cross_rate(*leg_rates: float) -> float:
    if not leg_rates:
        raise ValueError("Se necesita al menos una cotización para calcular el cruce.")
    result = 1.0
    for raw_rate in leg_rates:
        rate = float(raw_rate)
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError("Todas las cotizaciones del cruce deben ser positivas y finitas.")
        result *= rate
    if not math.isfinite(result) or result <= 0:
        raise ValueError("El cruce produjo una cotización inválida.")
    return result


def route_from_provider_pair(
    pair: FxPair,
    provider_pair: ProviderPair,
    *,
    inverted: bool,
) -> FxRoute:
    leg = FxRouteLeg(
        source=pair.base,
        target=pair.quote,
        provider_pair=provider_pair,
        inverted=inverted,
    )
    return FxRoute(
        pair=pair,
        source_type=FxSourceType.INVERSE if inverted else FxSourceType.DIRECT,
        legs=(leg,),
    )


class FxRoutingEngine:
    def __init__(
        self,
        registry: CurrencyRegistry,
        *,
        preferred_bridges: tuple[str, ...] = ("USD", "EUR"),
        max_intermediaries: int = 2,
    ) -> None:
        if max_intermediaries < 0 or max_intermediaries > 2:
            raise ValueError("El routing FX admite entre 0 y 2 intermediarios.")
        self.registry = registry
        self.preferred_bridges = preferred_bridges
        self.max_intermediaries = max_intermediaries

    def find_routes(self, pair: FxPair) -> tuple[FxRoute, ...]:
        self.registry.validate_pair(pair)
        adjacency: dict[str, list[FxRouteLeg]] = {}
        for provider_pair in self.registry.provider_pairs():
            direct = FxRouteLeg(
                source=provider_pair.base,
                target=provider_pair.quote,
                provider_pair=provider_pair,
                inverted=False,
            )
            inverse = FxRouteLeg(
                source=provider_pair.quote,
                target=provider_pair.base,
                provider_pair=provider_pair,
                inverted=True,
            )
            adjacency.setdefault(direct.source, []).append(direct)
            adjacency.setdefault(inverse.source, []).append(inverse)

        max_legs = self.max_intermediaries + 1
        queue: deque[tuple[str, tuple[FxRouteLeg, ...], frozenset[str]]] = deque(
            [(pair.base, (), frozenset({pair.base}))]
        )
        found: list[FxRoute] = []
        while queue:
            currency, legs, visited = queue.popleft()
            if len(legs) >= max_legs:
                continue
            candidates = sorted(
                adjacency.get(currency, ()),
                key=lambda leg: self._leg_priority(leg, pair.quote),
            )
            for leg in candidates:
                if leg.target in visited:
                    continue
                next_legs = (*legs, leg)
                if leg.target == pair.quote:
                    source_type = (
                        FxSourceType.INVERSE
                        if len(next_legs) == 1 and next_legs[0].inverted
                        else FxSourceType.DIRECT if len(next_legs) == 1 else FxSourceType.SYNTHETIC
                    )
                    found.append(FxRoute(pair, source_type, next_legs))
                    continue
                queue.append((leg.target, next_legs, visited | {leg.target}))

        found.sort(key=self._route_priority)
        return tuple(found)

    def resolve(self, pair: FxPair) -> FxRoute:
        routes = self.find_routes(pair)
        if not routes:
            raise ValueError(f"No existe una ruta FX fiable para {pair.display}.")
        return routes[0]

    def _leg_priority(self, leg: FxRouteLeg, target: str) -> tuple[int, int, str]:
        if leg.target == target:
            target_priority = -1
        else:
            try:
                target_priority = self.preferred_bridges.index(leg.target)
            except ValueError:
                target_priority = len(self.preferred_bridges)
        return target_priority, int(leg.inverted), leg.target

    def _route_priority(self, route: FxRoute) -> tuple[int, tuple[int, ...], str]:
        bridge_ranks: list[int] = []
        for bridge in route.currency_path[1:-1]:
            try:
                bridge_ranks.append(self.preferred_bridges.index(bridge))
            except ValueError:
                bridge_ranks.append(len(self.preferred_bridges))
        return len(route.legs), tuple(bridge_ranks), route.calculation_path
