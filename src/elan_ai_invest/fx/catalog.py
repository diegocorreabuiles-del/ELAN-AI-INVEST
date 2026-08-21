from __future__ import annotations

import pandas as pd

from elan_ai_invest.instruments import normalize_search_text

from .models import FxPair, normalize_fx_pair
from .registry import CurrencyRegistry

DEFAULT_COUNTER_CURRENCIES = ("USD", "EUR")


def build_virtual_fx_catalog(registry: CurrencyRegistry) -> pd.DataFrame:
    currencies = registry.enabled()
    rows: list[dict[str, object]] = []
    for base in currencies:
        for quote in currencies:
            if base.code == quote.code:
                continue
            pair = FxPair(base.code, quote.code)
            rows.append(
                {
                    "asset_id": pair.asset_id,
                    "asset_type": "FX",
                    "base_currency": base.code,
                    "quote_currency": quote.code,
                    "pair": pair.display,
                    "name": f"{base.name} / {quote.name}",
                    "label": f"{pair.display} — {base.name} / {quote.name}",
                    "_search": normalize_search_text(
                        " ".join(
                            (
                                pair.asset_id,
                                pair.display,
                                base.code,
                                quote.code,
                                base.name,
                                quote.name,
                                base.country,
                                quote.country,
                                base.region,
                                quote.region,
                            )
                        )
                    ),
                }
            )
    return pd.DataFrame(rows)


def search_fx_pairs(
    catalog: pd.DataFrame,
    query: str,
    *,
    limit: int = 100,
) -> pd.DataFrame:
    if catalog.empty or limit <= 0:
        return catalog.iloc[0:0].copy()
    terms = normalize_search_text(query).split()
    mask = pd.Series(True, index=catalog.index)
    for term in terms:
        mask &= catalog["_search"].str.contains(term, regex=False, na=False)
    result = catalog.loc[mask].copy()
    normalized_query = normalize_search_text(query)
    pair_query: FxPair | None = None
    try:
        pair_query = normalize_fx_pair(query)
    except ValueError:
        pass
    result["_priority"] = 0
    if pair_query is not None:
        result["_priority"] += result["asset_id"].eq(pair_query.asset_id).astype(int) * 100
    result["_priority"] += (
        result["pair"].map(normalize_search_text).eq(normalized_query).astype(int) * 80
    )
    result["_priority"] += result["base_currency"].isin(DEFAULT_COUNTER_CURRENCIES).astype(int) * 4
    result["_priority"] += result["quote_currency"].isin(DEFAULT_COUNTER_CURRENCIES).astype(int) * 8
    result = result.sort_values(
        ["_priority", "base_currency", "quote_currency"],
        ascending=[False, True, True],
    ).drop(columns="_priority")
    return result.head(limit).reset_index(drop=True)
