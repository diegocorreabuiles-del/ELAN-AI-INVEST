from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from .models import Currency, FxPair, ProviderPair, normalize_currency_code

REGISTRY_COLUMNS = (
    "code",
    "name",
    "symbol",
    "region",
    "country",
    "decimal_precision",
    "enabled",
    "data_provider",
    "provider_symbol",
    "provider_base",
    "provider_quote",
    "last_updated",
)


class CurrencyRegistry:
    def __init__(self, currencies: list[Currency]) -> None:
        by_code: dict[str, Currency] = {}
        for currency in currencies:
            code = normalize_currency_code(currency.code)
            if code in by_code:
                raise ValueError(f"Divisa duplicada en el registro: {code}")
            by_code[code] = currency
        if "USD" not in by_code:
            raise ValueError("El registro FX debe incluir USD.")
        self._currencies = by_code

    @classmethod
    def from_csv(cls, path: Path) -> CurrencyRegistry:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        missing = set(REGISTRY_COLUMNS).difference(frame.columns)
        if missing:
            raise ValueError(f"Faltan columnas en {path.name}: {', '.join(sorted(missing))}")
        currencies: list[Currency] = []
        for row in frame.loc[:, REGISTRY_COLUMNS].to_dict(orient="records"):
            code = normalize_currency_code(row["code"])
            precision = int(row["decimal_precision"])
            if not 0 <= precision <= 12:
                raise ValueError(f"Precisión inválida para {code}: {precision}")
            enabled_text = row["enabled"].strip().casefold()
            if enabled_text not in {"true", "false", "1", "0", "yes", "no"}:
                raise ValueError(f"Valor enabled inválido para {code}: {row['enabled']}")
            enabled = enabled_text in {"true", "1", "yes"}
            provider_symbol = row["provider_symbol"].strip() or None
            provider_base = row["provider_base"].strip().upper() or None
            provider_quote = row["provider_quote"].strip().upper() or None
            if provider_symbol and (not provider_base or not provider_quote):
                raise ValueError(f"Falta orientación del símbolo proveedor para {code}.")
            if provider_base:
                normalize_currency_code(provider_base)
            if provider_quote:
                normalize_currency_code(provider_quote)
            currencies.append(
                Currency(
                    code=code,
                    name=row["name"].strip(),
                    symbol=row["symbol"].strip(),
                    region=row["region"].strip(),
                    country=row["country"].strip(),
                    decimal_precision=precision,
                    enabled=enabled,
                    data_provider=row["data_provider"].strip(),
                    provider_symbol=provider_symbol,
                    provider_base=provider_base,
                    provider_quote=provider_quote,
                    last_updated=row["last_updated"].strip(),
                )
            )
        return cls(currencies)

    def __contains__(self, code: object) -> bool:
        try:
            normalized = normalize_currency_code(code)
        except ValueError:
            return False
        return normalized in self._currencies

    def get(self, code: object) -> Currency:
        normalized = normalize_currency_code(code)
        try:
            return self._currencies[normalized]
        except KeyError as exc:
            raise ValueError(f"Divisa no soportada: {normalized}") from exc

    def enabled(self) -> tuple[Currency, ...]:
        return tuple(currency for currency in self._currencies.values() if currency.enabled)

    def codes(self) -> tuple[str, ...]:
        return tuple(currency.code for currency in self.enabled())

    def validate_pair(self, pair: FxPair) -> FxPair:
        self.get(pair.base)
        self.get(pair.quote)
        return pair

    def provider_pairs(self) -> tuple[ProviderPair, ...]:
        pairs: dict[tuple[str, str, str, str], ProviderPair] = {}
        for currency in self.enabled():
            if not (
                currency.data_provider
                and currency.provider_symbol
                and currency.provider_base
                and currency.provider_quote
            ):
                continue
            pair = ProviderPair(
                provider=currency.data_provider,
                symbol=currency.provider_symbol,
                base=currency.provider_base,
                quote=currency.provider_quote,
            )
            key = (pair.provider, pair.symbol, pair.base, pair.quote)
            pairs[key] = pair
        return tuple(pairs.values())

    def search(self, query: str) -> tuple[Currency, ...]:
        terms = _normalize_search(query).split()
        if not terms:
            return self.enabled()
        result: list[Currency] = []
        for currency in self.enabled():
            haystack = _normalize_search(
                " ".join(
                    (
                        currency.code,
                        currency.name,
                        currency.country,
                        currency.region,
                    )
                )
            )
            if all(term in haystack for term in terms):
                result.append(currency)
        return tuple(result)


def _normalize_search(value: object) -> str:
    import unicodedata

    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.casefold().split())


def default_registry_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "currencies.csv"


@lru_cache(maxsize=4)
def load_currency_registry(path: Path | None = None) -> CurrencyRegistry:
    return CurrencyRegistry.from_csv((path or default_registry_path()).resolve())
