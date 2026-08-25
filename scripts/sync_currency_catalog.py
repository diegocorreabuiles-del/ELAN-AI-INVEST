from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ISO_LIST_URL = (
    "https://www.six-group.com/dam/download/financial-information/"
    "data-center/iso-currrency/lists/list-one.xml"
)
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
USER_AGENT = "ELAN-AI-INVEST currency catalog sync/1.0"
DEFAULT_MINIMUM_ENABLED = 100

FIELDNAMES = (
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

# List One also contains fund, precious-metal and testing codes. They are not
# sovereign/circulating currencies and belong in other asset classes.
NON_CURRENCY_CODES = frozenset(
    {
        "BOV",
        "CHE",
        "CHW",
        "CLF",
        "COU",
        "MXV",
        "USN",
        "UYI",
        "UYW",
        "XAD",
        "XAG",
        "XAU",
        "XBA",
        "XBB",
        "XBC",
        "XBD",
        "XDR",
        "XPD",
        "XPT",
        "XSU",
        "XTS",
        "XUA",
        "XXX",
    }
)

CORE_ORDER = (
    "USD",
    "EUR",
    "GBP",
    "JPY",
    "CHF",
    "CAD",
    "AUD",
    "NZD",
    "COP",
    "MXN",
    "CLP",
    "BRL",
    "ARS",
    "PEN",
    "UYU",
    "PYG",
    "BOB",
    "CRC",
    "DOP",
    "GTQ",
    "HNL",
    "CNY",
    "HKD",
    "SGD",
    "INR",
    "KRW",
    "TRY",
    "ZAR",
    "SEK",
    "NOK",
    "DKK",
    "PLN",
    "CZK",
    "HUF",
    "AED",
    "SAR",
)


def _ssl_context(insecure: bool) -> ssl.SSLContext:
    context = ssl.create_default_context()
    if insecure:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


def _download(url: str, *, insecure: bool, timeout: float = 30.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=_ssl_context(insecure),
    ) as response:
        return response.read()


def load_iso_currencies(*, insecure: bool = False) -> dict[str, dict[str, object]]:
    root = ET.fromstring(_download(ISO_LIST_URL, insecure=insecure))
    currencies: dict[str, dict[str, object]] = {}
    for node in root.findall(".//CcyNtry"):
        code = (node.findtext("Ccy") or "").strip().upper()
        if len(code) != 3 or not code.isalpha() or code in NON_CURRENCY_CODES:
            continue
        name = (node.findtext("CcyNm") or code).strip()
        country = (node.findtext("CtryNm") or "").strip()
        precision_text = (node.findtext("CcyMnrUnts") or "2").strip()
        precision = int(precision_text) if precision_text.isdigit() else 2
        item = currencies.setdefault(
            code,
            {"name": name, "countries": [], "precision": precision},
        )
        countries = item["countries"]
        if isinstance(countries, list) and country and country not in countries:
            countries.append(country)
    return currencies


def _load_existing(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {row["code"].strip().upper(): row for row in csv.DictReader(handle)}


def _provider_candidates(
    code: str,
    existing: dict[str, str] | None,
) -> tuple[tuple[str, str, str], ...]:
    candidates: list[tuple[str, str, str]] = []
    if existing and existing.get("provider_symbol"):
        candidates.append(
            (
                existing["provider_symbol"].strip(),
                existing["provider_base"].strip().upper(),
                existing["provider_quote"].strip().upper(),
            )
        )
    candidates.extend(
        (
            (f"{code}=X", "USD", code),
            (f"{code}USD=X", code, "USD"),
            (f"USD{code}=X", "USD", code),
        )
    )
    return tuple(dict.fromkeys(candidates))


def _yahoo_symbol_has_history(symbol: str, *, insecure: bool) -> bool:
    encoded = urllib.parse.quote(symbol, safe="")
    url = YAHOO_CHART_URL.format(symbol=encoded) + "?range=1mo&interval=1d"
    try:
        payload = json.loads(_download(url, insecure=insecure, timeout=12.0))
        result = payload.get("chart", {}).get("result")
        if not result:
            return False
        timestamps = result[0].get("timestamp") or []
        closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close") or []
        usable_closes = [value for value in closes if value is not None]
        return len(timestamps) >= 2 and len(usable_closes) >= 2
    except (OSError, TimeoutError, ValueError, json.JSONDecodeError):
        return False


def detect_yahoo_pair(
    code: str,
    existing: dict[str, str] | None,
    *,
    insecure: bool,
) -> tuple[str, str, str] | None:
    if code == "USD":
        return None
    for candidate in _provider_candidates(code, existing):
        if _yahoo_symbol_has_history(candidate[0], insecure=insecure):
            return candidate
    return None


def _catalog_order(code: str) -> tuple[int, int | str]:
    try:
        return 0, CORE_ORDER.index(code)
    except ValueError:
        return 1, code


def build_rows(
    iso_currencies: dict[str, dict[str, object]],
    existing: dict[str, dict[str, str]],
    provider_pairs: dict[str, tuple[str, str, str] | None],
    *,
    updated_on: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for code in sorted(iso_currencies, key=_catalog_order):
        iso = iso_currencies[code]
        previous = existing.get(code, {})
        provider_pair = provider_pairs.get(code)
        enabled = code == "USD" or provider_pair is not None
        countries = iso["countries"]
        country = previous.get("country", "").strip()
        if not country and isinstance(countries, list):
            country = "; ".join(countries)
        row: dict[str, object] = {
            "code": code,
            "name": previous.get("name", "").strip() or str(iso["name"]),
            "symbol": previous.get("symbol", "").strip() or code,
            "region": previous.get("region", "").strip() or "Global FX",
            "country": country,
            "decimal_precision": int(iso["precision"]),
            "enabled": str(enabled).lower(),
            "data_provider": "Yahoo" if provider_pair else "",
            "provider_symbol": provider_pair[0] if provider_pair else "",
            "provider_base": provider_pair[1] if provider_pair else "",
            "provider_quote": provider_pair[2] if provider_pair else "",
            "last_updated": updated_on,
        }
        rows.append(row)
    return rows


def sync_catalog(
    output: Path,
    *,
    insecure: bool = False,
    max_workers: int = 8,
    minimum_enabled: int = DEFAULT_MINIMUM_ENABLED,
) -> dict[str, object]:
    iso_currencies = load_iso_currencies(insecure=insecure)
    existing = _load_existing(output)
    provider_pairs: dict[str, tuple[str, str, str] | None] = {"USD": None}
    codes = [code for code in iso_currencies if code != "USD"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                detect_yahoo_pair,
                code,
                existing.get(code),
                insecure=insecure,
            ): code
            for code in codes
        }
        for future in concurrent.futures.as_completed(futures):
            provider_pairs[futures[future]] = future.result()

    rows = build_rows(
        iso_currencies,
        existing,
        provider_pairs,
        updated_on=date.today().isoformat(),
    )
    enabled = [row["code"] for row in rows if row["enabled"] == "true"]
    if len(enabled) < minimum_enabled:
        raise RuntimeError(
            "Sincronización FX cancelada: "
            f"solo {len(enabled)} monedas utilizables; mínimo {minimum_enabled}."
        )

    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(output)
    unavailable = [row["code"] for row in rows if row["enabled"] == "false"]
    return {
        "iso_currencies": len(rows),
        "enabled": len(enabled),
        "virtual_pairs": len(enabled) * (len(enabled) - 1),
        "unavailable": unavailable,
        "output": str(output),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sincroniza el catálogo FX ISO 4217 con disponibilidad Yahoo."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("config/currencies.csv"),
    )
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--minimum-enabled", type=int, default=DEFAULT_MINIMUM_ENABLED)
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Desactiva TLS solo para proxies locales con certificado autofirmado.",
    )
    args = parser.parse_args()
    if not 1 <= args.max_workers <= 16:
        parser.error("--max-workers debe estar entre 1 y 16")
    if args.minimum_enabled < 1:
        parser.error("--minimum-enabled debe ser positivo")
    result = sync_catalog(
        args.output.resolve(),
        insecure=args.insecure,
        max_workers=args.max_workers,
        minimum_enabled=args.minimum_enabled,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
