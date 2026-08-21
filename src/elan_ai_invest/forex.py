from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from elan_ai_invest.fx.registry import load_currency_registry


@dataclass(frozen=True)
class CurrencySpec:
    code: str
    name: str
    yahoo_symbol: str
    invert: bool = False


def _legacy_currency_specs() -> dict[str, CurrencySpec]:
    registry = load_currency_registry()
    specs: dict[str, CurrencySpec] = {}
    for currency in registry.enabled():
        if currency.code == "USD" or not currency.provider_symbol:
            continue
        invert = currency.provider_base == "USD" and currency.provider_quote == currency.code
        specs[currency.code] = CurrencySpec(
            currency.code,
            currency.name,
            currency.provider_symbol,
            invert=invert,
        )
    return specs


CURRENCY_SPECS = _legacy_currency_specs()
DEFAULT_CURRENCIES = ("EUR", "GBP", "JPY", "COP")


@dataclass(frozen=True)
class ForexAnalysis:
    prices_usd: pd.DataFrame
    normalized: pd.DataFrame
    returns: pd.DataFrame
    correlation: pd.DataFrame
    rolling_correlation: pd.Series
    summary: pd.DataFrame


def normalize_fx_prices(raw_prices: pd.DataFrame, currencies: tuple[str, ...]) -> pd.DataFrame:
    normalized: dict[str, pd.Series] = {}
    for code in dict.fromkeys(currencies):
        spec = CURRENCY_SPECS.get(code)
        if spec is None:
            raise ValueError(f"Divisa no soportada: {code}")
        if spec.yahoo_symbol not in raw_prices:
            continue
        series = pd.to_numeric(raw_prices[spec.yahoo_symbol], errors="coerce")
        series = series.replace([np.inf, -np.inf], np.nan).where(series > 0)
        normalized[code] = series.rdiv(1.0) if spec.invert else series

    if not normalized:
        return pd.DataFrame(index=raw_prices.index)
    return pd.DataFrame(normalized).sort_index().dropna(axis=1, how="all")


def build_forex_analysis(
    prices_usd: pd.DataFrame,
    first_currency: str,
    second_currency: str,
    *,
    window: int = 60,
) -> ForexAnalysis:
    if first_currency == second_currency:
        raise ValueError("Selecciona dos divisas distintas.")
    if first_currency not in prices_usd or second_currency not in prices_usd:
        raise ValueError("Una de las divisas focales no tiene datos.")
    if window < 2:
        raise ValueError("La ventana de correlación debe ser de al menos 2 sesiones.")

    aligned = prices_usd.apply(pd.to_numeric, errors="coerce")
    aligned = aligned.replace([np.inf, -np.inf], np.nan).where(aligned > 0).dropna()
    if len(aligned) < 3 or aligned.shape[1] < 2:
        raise ValueError("No hay suficientes sesiones alineadas para comparar divisas.")

    returns = aligned.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).dropna()
    if len(returns) < 2:
        raise ValueError("No hay suficientes rendimientos consecutivos para correlacionar.")

    normalized = aligned.div(aligned.iloc[0]).mul(100.0)
    correlation = returns.corr()
    minimum_periods = min(20, window)
    rolling = (
        returns[first_currency]
        .rolling(window, min_periods=minimum_periods)
        .corr(returns[second_currency])
        .dropna()
    )
    rolling.name = "Correlación"
    summary = pd.DataFrame(
        {
            "currency": aligned.columns,
            "latest_usd": aligned.iloc[-1].to_numpy(),
            "period_return_pct": aligned.iloc[-1].div(aligned.iloc[0]).sub(1.0).mul(100).to_numpy(),
            "volatility_pct": returns.std(ddof=1).mul(np.sqrt(252)).mul(100).to_numpy(),
            "observations": len(aligned),
        }
    )
    return ForexAnalysis(aligned, normalized, returns, correlation, rolling, summary)
