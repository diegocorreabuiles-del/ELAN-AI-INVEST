from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import pandas as pd

_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
_ASSET_ID_PATTERN = re.compile(r"^FX_([A-Z]{3})_([A-Z]{3})$")


class FxSourceType(StrEnum):
    DIRECT = "DIRECT"
    INVERSE = "INVERSE"
    SYNTHETIC = "SYNTHETIC"


@dataclass(frozen=True)
class Currency:
    code: str
    name: str
    symbol: str
    region: str
    country: str
    decimal_precision: int
    enabled: bool
    data_provider: str
    provider_symbol: str | None
    provider_base: str | None
    provider_quote: str | None
    last_updated: str


@dataclass(frozen=True)
class FxPair:
    base: str
    quote: str

    def __post_init__(self) -> None:
        base = normalize_currency_code(self.base)
        quote = normalize_currency_code(self.quote)
        if base == quote:
            raise ValueError("La divisa base y la cotizada deben ser distintas.")
        object.__setattr__(self, "base", base)
        object.__setattr__(self, "quote", quote)

    @property
    def asset_id(self) -> str:
        return f"FX_{self.base}_{self.quote}"

    @property
    def display(self) -> str:
        return f"{self.base}/{self.quote}"

    def inverse(self) -> FxPair:
        return FxPair(self.quote, self.base)


@dataclass(frozen=True)
class ProviderPair:
    provider: str
    symbol: str
    base: str
    quote: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "base", normalize_currency_code(self.base))
        object.__setattr__(self, "quote", normalize_currency_code(self.quote))
        if self.base == self.quote:
            raise ValueError("Un par de proveedor no puede tener monedas iguales.")
        if not self.provider.strip() or not self.symbol.strip():
            raise ValueError("El proveedor y su símbolo son obligatorios.")

    @property
    def pair(self) -> FxPair:
        return FxPair(self.base, self.quote)


@dataclass(frozen=True)
class FxRouteLeg:
    source: str
    target: str
    provider_pair: ProviderPair
    inverted: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", normalize_currency_code(self.source))
        object.__setattr__(self, "target", normalize_currency_code(self.target))

    @property
    def calculation(self) -> str:
        pair = self.provider_pair.pair.display
        return f"1 / {pair}" if self.inverted else pair


@dataclass(frozen=True)
class FxRoute:
    pair: FxPair
    source_type: FxSourceType
    legs: tuple[FxRouteLeg, ...]

    @property
    def provider(self) -> str:
        providers = list(dict.fromkeys(leg.provider_pair.provider for leg in self.legs))
        return " + ".join(providers)

    @property
    def calculation_path(self) -> str:
        return " × ".join(leg.calculation for leg in self.legs)

    @property
    def currency_path(self) -> tuple[str, ...]:
        if not self.legs:
            return (self.pair.base, self.pair.quote)
        return (self.legs[0].source, *(leg.target for leg in self.legs))


@dataclass(frozen=True)
class FxHistory:
    pair: FxPair
    prices: pd.DataFrame
    route: FxRoute
    coverage_ratio: float
    market_timestamp: pd.Timestamp
    received_at: datetime

    @property
    def observations(self) -> int:
        return len(self.prices)


def normalize_currency_code(value: object) -> str:
    code = str(value or "").strip().upper()
    if not _CURRENCY_PATTERN.fullmatch(code):
        raise ValueError(f"Código de divisa inválido: {value!r}")
    return code


def normalize_fx_pair(value: object, quote: object | None = None) -> FxPair:
    if isinstance(value, FxPair):
        if quote is not None:
            raise ValueError("No indiques una cotizada adicional para un FxPair.")
        return value
    if quote is not None:
        return FxPair(normalize_currency_code(value), normalize_currency_code(quote))

    text = str(value or "").strip().upper().replace("-", "/")
    asset_match = _ASSET_ID_PATTERN.fullmatch(text)
    if asset_match:
        return FxPair(*asset_match.groups())
    if "/" in text:
        parts = [part.strip() for part in text.split("/")]
        if len(parts) == 2:
            return FxPair(parts[0], parts[1])
    compact = text.replace(" ", "")
    if len(compact) == 6 and compact.isalpha():
        return FxPair(compact[:3], compact[3:])
    raise ValueError(f"Par FX inválido: {value!r}")


def is_fx_asset_id(value: object) -> bool:
    return bool(_ASSET_ID_PATTERN.fullmatch(str(value or "").strip().upper()))
