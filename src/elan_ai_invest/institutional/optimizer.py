from __future__ import annotations

from dataclasses import dataclass
from math import ceil

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class InstitutionalPortfolio:
    method: str
    weights: pd.Series
    annual_return_pct: float
    annual_volatility_pct: float
    sharpe: float
    diversification_ratio: float


def _clean_returns(prices: pd.DataFrame) -> pd.DataFrame:
    returns = prices.pct_change().replace([np.inf, -np.inf], np.nan).dropna(how="all")
    return returns.dropna(axis=1, thresh=max(30, int(len(returns) * 0.8))).fillna(0.0)


def _normalise(weights: np.ndarray, max_weight: float) -> np.ndarray:
    raw = np.maximum(np.asarray(weights, dtype=float), 0.0)
    asset_count = len(raw)
    if asset_count == 0:
        raise ValueError("No hay activos para normalizar")
    if not 0 < max_weight <= 1:
        raise ValueError("max_weight debe estar entre 0 y 1")
    if asset_count * max_weight < 1 - 1e-12:
        minimum_assets = ceil(1 / max_weight)
        raise ValueError(
            "Restricción max_weight inviable: "
            f"{asset_count} activos no pueden sumar el 100% con un máximo de "
            f"{max_weight:.2%}; se necesitan al menos {minimum_assets} activos"
        )

    result = np.zeros(asset_count, dtype=float)
    active = np.ones(asset_count, dtype=bool)
    remaining = 1.0

    while active.any():
        active_raw = raw[active]
        if active_raw.sum() <= 0:
            allocation = np.full(active.sum(), remaining / active.sum())
        else:
            allocation = remaining * active_raw / active_raw.sum()

        capped = allocation > max_weight + 1e-12
        if not capped.any():
            result[active] = allocation
            break

        active_indexes = np.flatnonzero(active)
        capped_indexes = active_indexes[capped]
        result[capped_indexes] = max_weight
        active[capped_indexes] = False
        remaining = 1.0 - float(result.sum())

    if abs(float(result.sum()) - 1.0) > 1e-9 or float(result.max()) > max_weight + 1e-9:
        raise RuntimeError("No se pudo construir una cartera que respete max_weight")
    return result


def _statistics(returns: pd.DataFrame, weights: np.ndarray) -> tuple[float, float, float, float]:
    mean = returns.mean().to_numpy() * 252
    covariance = returns.cov().to_numpy() * 252
    annual_return = float(mean @ weights)
    annual_volatility = float(np.sqrt(max(weights @ covariance @ weights, 0)))
    sharpe = annual_return / annual_volatility if annual_volatility > 0 else 0.0
    asset_volatility = np.sqrt(np.clip(np.diag(covariance), 0, None))
    weighted_asset_volatility = float(weights @ asset_volatility)
    diversification = (
        weighted_asset_volatility / annual_volatility if annual_volatility > 0 else 1.0
    )
    return annual_return * 100, annual_volatility * 100, sharpe, diversification


def optimize_portfolio(
    prices: pd.DataFrame,
    method: str = "risk_parity",
    max_weight: float = 0.25,
) -> InstitutionalPortfolio:
    returns = _clean_returns(prices)
    if returns.empty or returns.shape[1] == 0:
        raise ValueError("No hay retornos suficientes para optimizar")

    covariance = returns.cov().to_numpy() * 252
    volatilities = np.sqrt(np.clip(np.diag(covariance), 1e-12, None))

    if method == "equal_weight":
        raw = np.ones(len(volatilities))
    elif method == "minimum_variance":
        inverse = np.linalg.pinv(covariance)
        raw = inverse @ np.ones(len(volatilities))
        raw = np.maximum(raw, 0)
    elif method == "maximum_diversification":
        inverse = np.linalg.pinv(covariance)
        raw = inverse @ volatilities
        raw = np.maximum(raw, 0)
    else:
        method = "risk_parity"
        raw = 1 / volatilities

    weights = _normalise(raw, max_weight=max_weight)
    annual_return, annual_volatility, sharpe, diversification = _statistics(returns, weights)

    return InstitutionalPortfolio(
        method=method,
        weights=pd.Series(weights, index=returns.columns, name="weight"),
        annual_return_pct=round(annual_return, 2),
        annual_volatility_pct=round(annual_volatility, 2),
        sharpe=round(sharpe, 2),
        diversification_ratio=round(diversification, 2),
    )
