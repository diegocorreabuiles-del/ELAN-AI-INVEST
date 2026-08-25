from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from .models import AssetProfile, AssetType

_CATALOG_TYPES = {
    "stock": AssetType.EQUITY,
    "etf": AssetType.ETF,
    "crypto": AssetType.CRYPTO,
    "memecoin": AssetType.MEME_COIN,
    "stablecoin": AssetType.STABLECOIN,
    "forex": AssetType.FOREX,
    "bond": AssetType.BOND,
    "commodity": AssetType.COMMODITY,
    "index": AssetType.INDEX,
    "fund": AssetType.FUND,
}
_STABLECOINS = {
    "DAI-USD",
    "FDUSD-USD",
    "FRAX-USD",
    "GUSD-USD",
    "PYUSD-USD",
    "RLUSD-USD",
    "TUSD-USD",
    "USDC-USD",
    "USDD-USD",
    "USDE29470-USD",
    "USDT-USD",
}
_MEME_COINS = {
    "BONK-USD",
    "BRETT29743-USD",
    "DOGE-USD",
    "FARTCOIN-USD",
    "FLOKI-USD",
    "MOG-USD",
    "PENGU34466-USD",
    "PEPE24478-USD",
    "SHIB-USD",
    "SPX28081-USD",
    "TRUMP35336-USD",
    "TURBO-USD",
    "WIF-USD",
}
_EQUITY_SUFFIXES = (
    ".AD",
    ".AX",
    ".BO",
    ".DE",
    ".DU",
    ".F",
    ".HK",
    ".KS",
    ".KQ",
    ".L",
    ".MC",
    ".NS",
    ".SA",
    ".SS",
    ".SZ",
    ".T",
    ".TO",
    ".V",
)


def _clean(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _benchmark(asset_type: AssetType, country: str | None, exchange: str | None) -> str | None:
    if asset_type is AssetType.EQUITY:
        if country == "United States" and exchange == "NASDAQ":
            return "QQQ"
        return "SPY"
    if asset_type in {AssetType.CRYPTO, AssetType.MEME_COIN}:
        return "BTC-USD"
    return None


def _profile_from_row(symbol: str, row: Mapping[str, object]) -> AssetProfile:
    raw_type = _clean(row.get("asset_type"))
    asset_type = _CATALOG_TYPES.get((raw_type or "").casefold(), AssetType.UNKNOWN)
    country = _clean(row.get("country"))
    exchange = _clean(row.get("exchange"))
    return AssetProfile(
        symbol=symbol,
        name=_clean(row.get("name")) or symbol,
        asset_type=asset_type,
        catalog_asset_type=raw_type,
        country=country,
        exchange=exchange,
        benchmark=_benchmark(asset_type, country, exchange),
        classification_source="catalog",
        classification_confidence=100.0 if asset_type is not AssetType.UNKNOWN else 50.0,
    )


def _infer_profile(symbol: str) -> AssetProfile:
    from elan_ai_invest.fx.models import is_fx_asset_id

    if symbol in _STABLECOINS:
        asset_type = AssetType.STABLECOIN
    elif symbol in _MEME_COINS:
        asset_type = AssetType.MEME_COIN
    elif is_fx_asset_id(symbol) or symbol.endswith("=X"):
        asset_type = AssetType.FOREX
    elif symbol.startswith("^"):
        asset_type = AssetType.INDEX
    elif symbol.endswith("=F"):
        asset_type = AssetType.COMMODITY
    elif symbol.endswith("-USD"):
        asset_type = AssetType.CRYPTO
    elif symbol.endswith(_EQUITY_SUFFIXES):
        asset_type = AssetType.EQUITY
    else:
        asset_type = AssetType.UNKNOWN
    return AssetProfile(
        symbol=symbol,
        name=symbol,
        asset_type=asset_type,
        benchmark=_benchmark(asset_type, None, None),
        classification_source="symbol_heuristic",
        classification_confidence=70.0 if asset_type is not AssetType.UNKNOWN else 0.0,
    )


def classify_asset(symbol: str, catalog: pd.DataFrame | None = None) -> AssetProfile:
    """Classify an asset without querying external providers.

    Catalog metadata is authoritative. Symbol heuristics are deliberately conservative
    and expose a lower confidence so unknown manual symbols are never treated as equities
    merely because they contain letters.
    """

    normalized = str(symbol).strip().upper()
    if not normalized:
        raise ValueError("El símbolo del activo no puede estar vacío")
    if catalog is not None and not catalog.empty and "symbol" in catalog:
        matches = catalog.loc[catalog["symbol"].astype(str).str.upper().eq(normalized)]
        if not matches.empty:
            return _profile_from_row(normalized, matches.iloc[0].to_dict())
    return _infer_profile(normalized)
