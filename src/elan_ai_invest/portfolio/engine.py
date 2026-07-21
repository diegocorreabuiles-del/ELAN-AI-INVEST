from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PortfolioPlan:
    allocations: pd.DataFrame
    cash_weight_pct: float
    invested_weight_pct: float
    expected_volatility_pct: float
    risk_level: str


def build_portfolio(
    ranking: pd.DataFrame,
    asset_risk: pd.DataFrame,
    capital: float = 100_000.0,
    profile: str = "moderado",
    min_score: float = 55.0,
    max_positions: int = 8,
    max_position_pct: float = 15.0,
    min_cash_pct: float = 15.0,
) -> PortfolioPlan:
    if capital <= 0:
        raise ValueError("El capital debe ser mayor que cero")
    if max_positions <= 0:
        raise ValueError("max_positions debe ser mayor que cero")
    if not 0 < max_position_pct <= 100:
        raise ValueError("max_position_pct debe estar entre 0 y 100")
    if not 0 <= min_cash_pct <= 100:
        raise ValueError("min_cash_pct debe estar entre 0 y 100")
    if ranking.empty or asset_risk.empty:
        raise ValueError("Se necesitan ranking y riesgo por activo")

    ranking = ranking.copy()
    if "signal" not in ranking.columns:
        ranking["signal"] = "Neutral"
    risk_data = asset_risk.copy()
    if "risk_contribution_pct" not in risk_data.columns:
        risk_data["risk_contribution_pct"] = 0.0

    ranking_without_derived_risk = ranking.drop(columns=["volatility_pct"], errors="ignore")
    merged = ranking_without_derived_risk.merge(
        risk_data[["symbol", "volatility_pct", "risk_contribution_pct"]],
        on="symbol",
        how="inner",
    )
    merged = merged[merged["score"] >= min_score].copy()
    merged = merged.sort_values(["score", "confidence"], ascending=False).head(max_positions)

    if merged.empty:
        return PortfolioPlan(
            allocations=pd.DataFrame(
                columns=["symbol", "score", "weight_pct", "amount_eur", "volatility_pct"]
            ),
            cash_weight_pct=100.0,
            invested_weight_pct=0.0,
            expected_volatility_pct=0.0,
            risk_level="Bajo",
        )

    profile_key = profile.strip().lower()
    profile_cash = {"conservador": 30.0, "moderado": 20.0, "agresivo": 10.0}
    profile_cap = {"conservador": 10.0, "moderado": 15.0, "agresivo": 20.0}
    cash_pct = max(min_cash_pct, profile_cash.get(profile_key, 20.0))
    cap_pct = min(max_position_pct, profile_cap.get(profile_key, max_position_pct))
    investable_pct = 100.0 - cash_pct

    score_strength = merged["score"].clip(lower=min_score) - min_score + 5.0
    inverse_vol = 1.0 / merged["volatility_pct"].clip(lower=5.0)
    raw = score_strength * inverse_vol
    weights = raw / raw.sum() * investable_pct

    # Cap positions and redistribute residual iteratively.
    weights = weights.clip(upper=cap_pct)
    for _ in range(10):
        residual = investable_pct - float(weights.sum())
        if residual <= 1e-6:
            break
        eligible = weights < cap_pct - 1e-9
        if not eligible.any():
            break
        add = raw[eligible] / raw[eligible].sum() * residual
        weights.loc[eligible] = (weights.loc[eligible] + add).clip(upper=cap_pct)

    invested = float(weights.sum())
    cash_pct = 100.0 - invested
    merged["weight_pct"] = weights.values
    merged["amount_eur"] = merged["weight_pct"] / 100.0 * capital
    merged["estimated_daily_risk_eur"] = (
        merged["amount_eur"] * merged["volatility_pct"] / np.sqrt(252) / 100.0
    )

    expected_vol = float(
        np.sqrt(np.sum((merged["weight_pct"] / 100.0 * merged["volatility_pct"]) ** 2))
    )
    risk_level = "Bajo" if expected_vol < 10 else "Medio" if expected_vol < 18 else "Alto"

    columns = [
        "symbol",
        "score",
        "confidence",
        "signal",
        "weight_pct",
        "amount_eur",
        "volatility_pct",
        "risk_contribution_pct",
        "estimated_daily_risk_eur",
    ]
    return PortfolioPlan(
        allocations=merged[columns].sort_values("weight_pct", ascending=False, ignore_index=True),
        cash_weight_pct=float(cash_pct),
        invested_weight_pct=invested,
        expected_volatility_pct=expected_vol,
        risk_level=risk_level,
    )


def portfolio_equity_curve(
    prices: pd.DataFrame,
    allocations: pd.DataFrame,
    initial_capital: float,
) -> pd.DataFrame:
    if prices.empty or allocations.empty:
        return pd.DataFrame()
    weights = allocations.set_index("symbol")["weight_pct"] / 100.0
    available = [symbol for symbol in weights.index if symbol in prices.columns]
    if not available:
        return pd.DataFrame()
    clean = prices[available].sort_index().ffill().dropna(how="all")
    returns = clean.pct_change(fill_method=None).fillna(0.0)
    invested_returns = returns.mul(weights.reindex(available), axis=1).sum(axis=1)
    cash_weight = max(0.0, 1.0 - float(weights.reindex(available).sum()))
    total_returns = invested_returns + cash_weight * 0.0
    equity = initial_capital * (1.0 + total_returns).cumprod()
    result = pd.DataFrame({"portfolio": equity})
    if "SPY" in prices.columns:
        spy = prices["SPY"].reindex(result.index).ffill().dropna()
        if not spy.empty:
            result["SPY"] = initial_capital * spy / spy.iloc[0]
    return result.dropna(how="all")
