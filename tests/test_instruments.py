from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from elan_ai_invest.instruments import (
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
        "Crypto": {"BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD"},
        "Stablecoin": {"USDT-USD", "USDC-USD", "DAI-USD"},
        "Memecoin": {"DOGE-USD", "SHIB-USD", "PEPE24478-USD", "BONK-USD"},
    }
    for asset_type, symbols in expected.items():
        available = set(search_instruments(catalog, asset_type=asset_type)["symbol"])
        assert symbols <= available

    assert search_instruments(catalog, "pepe").iloc[0]["symbol"] == "PEPE24478-USD"
