from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PortfolioRiskReport:
    weights: pd.Series
    daily_returns: pd.Series
    annual_volatility_pct: float
    var_95_pct: float
    var_99_pct: float
    cvar_95_pct: float
    cvar_99_pct: float
    max_drawdown_pct: float
    diversification_ratio: float
    risk_level: str
    correlation: pd.DataFrame
    asset_risk: pd.DataFrame


def _clean_prices(prices: pd.DataFrame) -> pd.DataFrame:
    clean = prices.copy().sort_index().ffill().dropna(axis=1, how="all")
    clean = clean.dropna(how="all")
    if clean.shape[0] < 60 or clean.shape[1] == 0:
        raise ValueError("Se necesitan al menos 60 sesiones y un activo válido")
    return clean


def _normalise_weights(columns: pd.Index, weights: dict[str, float] | None) -> pd.Series:
    if not weights:
        return pd.Series(1.0 / len(columns), index=columns, dtype=float)
    raw = pd.Series({symbol: float(weights.get(symbol, 0.0)) for symbol in columns})
    if (raw < 0).any():
        raise ValueError("Los pesos no pueden ser negativos")
    total = float(raw.sum())
    if total <= 0:
        raise ValueError("La suma de pesos debe ser mayor que cero")
    return raw / total


def calculate_risk_report(
    prices: pd.DataFrame,
    weights: dict[str, float] | None = None,
    annualisation_days: int = 252,
) -> PortfolioRiskReport:
    clean = _clean_prices(prices)
    returns = clean.pct_change(fill_method=None).dropna(how="all").fillna(0.0)
    w = _normalise_weights(returns.columns, weights)
    portfolio_returns = returns.mul(w, axis=1).sum(axis=1)

    annual_vol = float(portfolio_returns.std(ddof=1) * np.sqrt(annualisation_days) * 100)
    var_95 = float(max(0.0, -np.quantile(portfolio_returns, 0.05) * 100))
    var_99 = float(max(0.0, -np.quantile(portfolio_returns, 0.01) * 100))

    tail_95 = portfolio_returns[portfolio_returns <= np.quantile(portfolio_returns, 0.05)]
    tail_99 = portfolio_returns[portfolio_returns <= np.quantile(portfolio_returns, 0.01)]
    cvar_95 = float(max(0.0, -tail_95.mean() * 100)) if not tail_95.empty else var_95
    cvar_99 = float(max(0.0, -tail_99.mean() * 100)) if not tail_99.empty else var_99

    equity = (1.0 + portfolio_returns).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    max_drawdown = float(drawdown.min() * 100)

    asset_vol = returns.std(ddof=1) * np.sqrt(annualisation_days)
    covariance = returns.cov() * annualisation_days
    portfolio_variance = float(w.T @ covariance @ w)
    portfolio_vol_decimal = float(np.sqrt(max(portfolio_variance, 0.0)))
    weighted_asset_vol = float((w * asset_vol).sum())
    diversification_ratio = (
        weighted_asset_vol / portfolio_vol_decimal if portfolio_vol_decimal > 0 else 1.0
    )

    marginal = covariance @ w
    component = w * marginal
    risk_contribution = component / portfolio_variance if portfolio_variance > 0 else component * 0

    asset_drawdown = clean.div(clean.cummax()).sub(1.0).min() * 100
    asset_risk = pd.DataFrame(
        {
            "symbol": returns.columns,
            "weight_pct": w.values * 100,
            "volatility_pct": asset_vol.values * 100,
            "max_drawdown_pct": asset_drawdown.reindex(returns.columns).values,
            "risk_contribution_pct": risk_contribution.values * 100,
        }
    ).sort_values("risk_contribution_pct", ascending=False, ignore_index=True)

    risk_level = _risk_level(annual_vol, abs(max_drawdown), cvar_95)
    return PortfolioRiskReport(
        weights=w,
        daily_returns=portfolio_returns,
        annual_volatility_pct=annual_vol,
        var_95_pct=var_95,
        var_99_pct=var_99,
        cvar_95_pct=cvar_95,
        cvar_99_pct=cvar_99,
        max_drawdown_pct=max_drawdown,
        diversification_ratio=float(diversification_ratio),
        risk_level=risk_level,
        correlation=returns.corr(),
        asset_risk=asset_risk,
    )


def suggested_position_size_pct(
    annual_volatility_pct: float,
    risk_budget_pct: float = 0.50,
    stop_multiple: float = 2.0,
    max_position_pct: float = 15.0,
) -> float:
    if annual_volatility_pct <= 0:
        return 0.0
    daily_vol_pct = annual_volatility_pct / np.sqrt(252)
    estimated_stop_pct = max(daily_vol_pct * stop_multiple, 1.0)
    size = risk_budget_pct / estimated_stop_pct * 100
    return float(np.clip(size, 0.0, max_position_pct))


def _risk_level(volatility_pct: float, drawdown_pct: float, cvar_95_pct: float) -> str:
    score = 0
    score += 2 if volatility_pct >= 25 else 1 if volatility_pct >= 16 else 0
    score += 2 if drawdown_pct >= 25 else 1 if drawdown_pct >= 15 else 0
    score += 2 if cvar_95_pct >= 3 else 1 if cvar_95_pct >= 2 else 0
    if score >= 5:
        return "Alto"
    if score >= 2:
        return "Medio"
    return "Bajo"
