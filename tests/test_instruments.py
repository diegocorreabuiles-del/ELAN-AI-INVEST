from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from elan_ai_invest.fx import load_currency_registry
from elan_ai_invest.instruments import (
    CRYPTO_ASSET_GROUP,
    load_instrument_catalog,
    normalize_custom_symbol,
    search_instruments,
    yahoo_symbol,
)


def _write_curated(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "symbol": "SAN.MC",
                "ticker": "SAN",
                "name": "Banco Santander",
                "asset_type": "Stock",
                "country": "Spain",
                "country_code": "ES",
                "exchange": "BME",
                "isin": "ES0113900J37",
                "aliases": "santander",
                "source": "test",
            },
            {
                "symbol": "GC=F",
                "ticker": "GC=F",
                "name": "Gold Futures",
                "asset_type": "Commodity",
                "country": "Global",
                "country_code": "",
                "exchange": "COMEX",
                "isin": "",
                "aliases": "oro",
                "source": "test",
            },
        ]
    ).to_csv(path, index=False)


def test_catalog_searches_symbol_name_isin_and_spanish_country_alias(tmp_path: Path) -> None:
    curated = tmp_path / "instruments.csv"
    _write_curated(curated)
    catalog = load_instrument_catalog(curated)

    assert search_instruments(catalog, "santander").iloc[0]["symbol"] == "SAN.MC"
    assert search_instruments(catalog, "ES0113900J37").iloc[0]["symbol"] == "SAN.MC"
    assert search_instruments(catalog, "España").iloc[0]["symbol"] == "SAN.MC"
    assert search_instruments(catalog, "oro").iloc[0]["symbol"] == "GC=F"


def test_catalog_filters_by_asset_country_and_exchange(tmp_path: Path) -> None:
    curated = tmp_path / "instruments.csv"
    _write_curated(curated)
    catalog = load_instrument_catalog(curated)

    result = search_instruments(
        catalog,
        asset_type="Stock",
        country="Spain",
        exchange="BME",
    )

    assert result["symbol"].tolist() == ["SAN.MC"]


@pytest.mark.parametrize(
    ("ticker", "exchange", "expected"),
    [
        ("AAPL", "NASDAQ", "AAPL"),
        ("SAN", "BME", "SAN.MC"),
        ("700", "HKEX", "0700.HK"),
        ("EMAAR", "DFM", "EMAAR.DU"),
        ("000001", "SZSE", "000001.SZ"),
    ],
)
def test_yahoo_symbol_maps_supported_exchanges(
    ticker: str,
    exchange: str,
    expected: str,
) -> None:
    assert yahoo_symbol(ticker, exchange) == expected


def test_curated_rows_take_priority_over_open_catalog(tmp_path: Path) -> None:
    curated = tmp_path / "instruments.csv"
    _write_curated(curated)
    open_catalog = tmp_path / "tickers.csv"
    pd.DataFrame(
        [
            {
                "ticker": "SAN",
                "name": "Duplicate Santander",
                "exchange": "BME",
                "asset_type": "Stock",
                "stock_sector": "Financials",
                "etf_category": "",
                "country": "Spain",
                "country_code": "ES",
                "isin": "ES0113900J37",
                "aliases": "",
            }
        ]
    ).to_csv(open_catalog, index=False)

    catalog = load_instrument_catalog(curated, open_catalog)

    assert catalog.loc[catalog["symbol"].eq("SAN.MC"), "name"].item() == "Banco Santander"


def test_custom_symbol_validation() -> None:
    assert normalize_custom_symbol(" 1810.hk ") == "1810.HK"
    assert normalize_custom_symbol("gc=f") == "GC=F"

    with pytest.raises(ValueError):
        normalize_custom_symbol("AAPL; Remove-Item")


def test_project_catalog_exposes_curated_crypto_groups() -> None:
    catalog_path = Path(__file__).parents[1] / "config" / "instruments.csv"
    catalog = load_instrument_catalog(catalog_path)

    expected = {
        "Crypto": {
            "BTC-USD",
            "ETH-USD",
            "BNB-USD",
            "SOL-USD",
            "XRP-USD",
            "TRX-USD",
            "SUI20947-USD",
            "KAS-USD",
        },
        "Stablecoin": {
            "USDT-USD",
            "USDC-USD",
            "DAI-USD",
            "FDUSD-USD",
            "PYUSD-USD",
            "USDE29470-USD",
        },
        "Memecoin": {
            "DOGE-USD",
            "SHIB-USD",
            "PEPE24478-USD",
            "BONK-USD",
            "WIF-USD",
            "TRUMP35336-USD",
            "PENGU34466-USD",
        },
    }
    expected_counts = {"Crypto": 30, "Stablecoin": 11, "Memecoin": 13}
    for asset_type, symbols in expected.items():
        available = search_instruments(catalog, asset_type=asset_type)
        assert symbols <= set(available["symbol"])
        assert len(available) == expected_counts[asset_type]

    cryptoassets = search_instruments(catalog, asset_type=CRYPTO_ASSET_GROUP)
    assert len(cryptoassets) == 54
    assert set(cryptoassets["asset_type"]) == {"Crypto", "Stablecoin", "Memecoin"}
    assert {"USDT-USD", "USDC-USD"} <= set(cryptoassets["symbol"])
    assert search_instruments(catalog, "pepe").iloc[0]["symbol"] == "PEPE24478-USD"


def test_project_catalog_replaces_legacy_forex_rows_with_fx_registry() -> None:
    root = Path(__file__).parents[1]
    currency_path = root / "config" / "currencies.csv"
    catalog = load_instrument_catalog(
        root / "config" / "instruments.csv",
        currency_registry_path=currency_path,
    )
    registry = load_currency_registry(currency_path)
    expected_symbols = {
        currency.provider_symbol for currency in registry.enabled() if currency.provider_symbol
    }
    forex = search_instruments(catalog, asset_type="Forex", limit=len(expected_symbols) + 1)

    assert set(forex["symbol"]) == expected_symbols
    assert len(forex) == 127
    assert "COP=X" in expected_symbols
    assert "COPUSD=X" not in set(forex["symbol"])
    assert search_instruments(
        catalog,
        asset_type="Forex",
        country="NIGERIA",
        exchange="FX",
    )[
        "symbol"
    ].tolist() == ["NGN=X"]
    assert search_instruments(catalog, "BCEAO", asset_type="Forex").iloc[0]["symbol"] == "XOF=X"
