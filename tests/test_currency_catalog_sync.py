from __future__ import annotations

from pathlib import Path

import pytest

from scripts import sync_currency_catalog
from scripts.sync_currency_catalog import build_rows


def test_catalog_sync_enables_only_verified_provider_pairs() -> None:
    iso_currencies = {
        "USD": {"name": "US Dollar", "countries": ["UNITED STATES"], "precision": 2},
        "EUR": {"name": "Euro", "countries": ["EURO AREA"], "precision": 2},
        "BTN": {"name": "Ngultrum", "countries": ["BHUTAN"], "precision": 2},
    }
    existing = {
        "EUR": {
            "name": "Euro",
            "symbol": "€",
            "region": "Europa",
            "country": "Zona euro",
        }
    }
    provider_pairs = {
        "USD": None,
        "EUR": ("EURUSD=X", "EUR", "USD"),
        "BTN": None,
    }

    rows = build_rows(
        iso_currencies,
        existing,
        provider_pairs,
        updated_on="2026-08-22",
    )
    by_code = {str(row["code"]): row for row in rows}

    assert [row["code"] for row in rows] == ["USD", "EUR", "BTN"]
    assert by_code["USD"]["enabled"] == "true"
    assert by_code["USD"]["data_provider"] == ""
    assert by_code["EUR"]["enabled"] == "true"
    assert by_code["EUR"]["provider_symbol"] == "EURUSD=X"
    assert by_code["EUR"]["symbol"] == "€"
    assert by_code["EUR"]["region"] == "Europa"
    assert by_code["BTN"]["enabled"] == "false"
    assert by_code["BTN"]["provider_symbol"] == ""


def test_catalog_sync_aborts_before_write_when_provider_coverage_collapses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    iso_currencies = {
        "USD": {"name": "US Dollar", "countries": ["UNITED STATES"], "precision": 2},
        "EUR": {"name": "Euro", "countries": ["EURO AREA"], "precision": 2},
    }
    monkeypatch.setattr(
        sync_currency_catalog,
        "load_iso_currencies",
        lambda **kwargs: iso_currencies,
    )
    monkeypatch.setattr(
        sync_currency_catalog,
        "detect_yahoo_pair",
        lambda *args, **kwargs: None,
    )
    output = tmp_path / "currencies.csv"

    with pytest.raises(RuntimeError, match="solo 1 monedas utilizables"):
        sync_currency_catalog.sync_catalog(output, minimum_enabled=2)

    assert not output.exists()
