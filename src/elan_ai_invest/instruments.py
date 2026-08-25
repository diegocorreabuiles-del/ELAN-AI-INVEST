from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

CATALOG_COLUMNS = (
    "symbol",
    "ticker",
    "name",
    "asset_type",
    "country",
    "country_code",
    "exchange",
    "isin",
    "aliases",
    "source",
)

YAHOO_EXCHANGE_SUFFIXES = {
    "ADX": ".AD",
    "ASX": ".AX",
    "B3": ".SA",
    "BME": ".MC",
    "BSE_IN": ".BO",
    "DFM": ".DU",
    "FWB": ".F",
    "HKEX": ".HK",
    "KRX": ".KS",
    "KOSDAQ": ".KQ",
    "LSE": ".L",
    "NSE_IN": ".NS",
    "SSE": ".SS",
    "SZSE": ".SZ",
    "TSE": ".T",
    "TSX": ".TO",
    "TSXV": ".V",
    "XETRA": ".DE",
}

COUNTRY_SEARCH_ALIASES = {
    "china": "china cn",
    "colombia": "colombia colombian co",
    "spain": "spain espana español española es",
    "united arab emirates": "united arab emirates emiratos arabes unidos emiratos uae ae",
    "united states": "united states estados unidos eeuu usa us",
}

ASSET_TYPE_LABELS = {
    "Bond": "Bono",
    "Commodity": "Materia prima",
    "Crypto": "Cripto",
    "Cryptoasset": "Criptoactivos (todos)",
    "ETF": "ETF",
    "Forex": "Divisa",
    "Fund": "Fondo",
    "Index": "Índice",
    "Memecoin": "Memecoin",
    "Stablecoin": "Stablecoin",
    "Stock": "Acción",
}

CRYPTO_ASSET_GROUP = "Cryptoasset"
CRYPTO_ASSET_TYPES = frozenset({"Crypto", "Memecoin", "Stablecoin"})

US_EXCHANGES = {"AMEX", "NASDAQ", "NYSE", "NYSE ARCA", "NYSE MKT"}
SAFE_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9^=._-]{1,32}$")


def normalize_search_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    without_accents = "".join(
        character for character in text if not unicodedata.combining(character)
    )
    return " ".join(without_accents.casefold().split())


def normalize_custom_symbol(value: str) -> str:
    symbol = value.strip().upper()
    if not SAFE_SYMBOL_PATTERN.fullmatch(symbol):
        raise ValueError(
            "Usa un símbolo de 1 a 32 caracteres con letras, números, punto, guion, "
            "guion bajo, ^ o =."
        )
    return symbol


def yahoo_symbol(ticker: object, exchange: object) -> str:
    normalized_ticker = str(ticker or "").strip().upper()
    normalized_exchange = str(exchange or "").strip().upper()
    if not normalized_ticker:
        return ""
    if normalized_exchange in US_EXCHANGES:
        return normalized_ticker.replace(".", "-")
    suffix = YAHOO_EXCHANGE_SUFFIXES.get(normalized_exchange, "")
    if normalized_exchange == "HKEX" and normalized_ticker.isdigit():
        normalized_ticker = normalized_ticker.zfill(4)
    return f"{normalized_ticker}{suffix}"


def _empty_catalog() -> pd.DataFrame:
    return pd.DataFrame(columns=CATALOG_COLUMNS)


def _read_curated_catalog(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return _empty_catalog()
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    required = {"symbol", "name", "asset_type"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Faltan columnas en {path.name}: {', '.join(sorted(missing))}")
    for column in CATALOG_COLUMNS:
        if column not in frame:
            frame[column] = ""
    frame["ticker"] = frame["ticker"].where(frame["ticker"].ne(""), frame["symbol"])
    frame["source"] = frame["source"].where(frame["source"].ne(""), "ELAN curated")
    return frame.loc[:, CATALOG_COLUMNS]


def _read_adanos_catalog(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return _empty_catalog()
    source = pd.read_csv(
        path,
        compression="infer",
        dtype=str,
        keep_default_na=False,
        usecols=[
            "ticker",
            "name",
            "exchange",
            "asset_type",
            "country",
            "country_code",
            "isin",
            "aliases",
        ],
    )
    source["symbol"] = [
        yahoo_symbol(ticker, exchange)
        for ticker, exchange in zip(source["ticker"], source["exchange"], strict=True)
    ]
    source["source"] = "Adanos Open Ticker Database"
    return source.loc[:, CATALOG_COLUMNS]


def _read_fx_currency_catalog(path: Path) -> pd.DataFrame:
    from elan_ai_invest.fx.registry import load_currency_registry

    rows: list[dict[str, str]] = []
    for currency in load_currency_registry(path).enabled():
        if not (currency.provider_symbol and currency.provider_base and currency.provider_quote):
            continue
        pair = f"{currency.provider_base}/{currency.provider_quote}"
        aliases = " ".join(
            dict.fromkeys(
                (
                    currency.code,
                    currency.name,
                    currency.region,
                    pair,
                    "forex",
                    "fx",
                    "divisa",
                )
            )
        )
        rows.append(
            {
                "symbol": currency.provider_symbol,
                "ticker": currency.provider_symbol,
                "name": f"{pair} - {currency.name}",
                "asset_type": "Forex",
                "country": currency.country,
                "country_code": "",
                "exchange": "FX",
                "isin": "",
                "aliases": aliases,
                "source": "ELAN FX registry",
            }
        )
    return pd.DataFrame(rows, columns=CATALOG_COLUMNS)


def load_instrument_catalog(
    curated_path: Path,
    open_catalog_path: Path | None = None,
    currency_registry_path: Path | None = None,
) -> pd.DataFrame:
    frames = [_read_curated_catalog(curated_path)]
    if open_catalog_path is not None:
        frames.append(_read_adanos_catalog(open_catalog_path))
    catalog = pd.concat(frames, ignore_index=True)
    if currency_registry_path is not None:
        catalog = catalog.loc[~catalog["asset_type"].str.strip().str.casefold().eq("forex")].copy()
        catalog = pd.concat(
            [catalog, _read_fx_currency_catalog(currency_registry_path)],
            ignore_index=True,
        )
    if catalog.empty:
        return _empty_catalog()

    for column in CATALOG_COLUMNS:
        catalog[column] = catalog[column].fillna("").astype(str).str.strip()
    catalog["symbol"] = catalog["symbol"].str.upper()
    catalog["ticker"] = catalog["ticker"].str.upper()
    catalog = catalog.loc[catalog["symbol"].ne("") & catalog["name"].ne("")].copy()
    catalog = catalog.drop_duplicates(subset=["symbol"], keep="first").reset_index(drop=True)

    country_aliases = catalog["country"].str.casefold().map(COUNTRY_SEARCH_ALIASES).fillna("")
    search_columns = [
        catalog["symbol"],
        catalog["ticker"],
        catalog["name"],
        catalog["asset_type"],
        catalog["country"],
        catalog["country_code"],
        catalog["exchange"],
        catalog["isin"],
        catalog["aliases"],
        country_aliases,
    ]
    catalog["_search"] = (
        search_columns[0].str.cat(search_columns[1:], sep=" ").map(normalize_search_text)
    )
    return catalog


def search_instruments(
    catalog: pd.DataFrame,
    query: str = "",
    asset_type: str | None = None,
    country: str | None = None,
    exchange: str | None = None,
    *,
    limit: int = 100,
) -> pd.DataFrame:
    if catalog.empty or limit <= 0:
        return catalog.iloc[0:0].copy()

    mask = pd.Series(True, index=catalog.index)
    if asset_type == CRYPTO_ASSET_GROUP:
        mask &= catalog["asset_type"].isin(CRYPTO_ASSET_TYPES)
    elif asset_type:
        mask &= catalog["asset_type"].eq(asset_type)
    if country:
        mask &= catalog["country"].eq(country)
    if exchange:
        mask &= catalog["exchange"].eq(exchange)

    terms = normalize_search_text(query).split()
    for term in terms:
        mask &= catalog["_search"].str.contains(re.escape(term), regex=True, na=False)

    result = catalog.loc[mask].copy()
    if terms:
        normalized_query = normalize_search_text(query)
        result["_priority"] = (
            result["symbol"].map(normalize_search_text).eq(normalized_query).astype(int) * 4
            + result["ticker"].map(normalize_search_text).eq(normalized_query).astype(int) * 3
            + result["name"].map(normalize_search_text).str.startswith(normalized_query).astype(int)
        )
        result = result.sort_values(
            ["_priority", "asset_type", "symbol"],
            ascending=[False, True, True],
        ).drop(columns="_priority")
    else:
        result = result.sort_values(["source", "asset_type", "symbol"])
    return result.head(limit).reset_index(drop=True)


def instrument_label(row: pd.Series) -> str:
    asset_type = ASSET_TYPE_LABELS.get(row.get("asset_type", ""), row.get("asset_type", ""))
    details = " · ".join(
        value
        for value in (
            asset_type,
            str(row.get("exchange", "")).strip(),
            str(row.get("country", "")).strip(),
        )
        if value
    )
    label = f"{row['symbol']} — {row['name']}"
    return f"{label} ({details})" if details else label


def labels_by_symbol(catalog: pd.DataFrame) -> dict[str, str]:
    return {
        str(row["symbol"]): instrument_label(row)
        for _, row in catalog.drop_duplicates("symbol", keep="first").iterrows()
    }
