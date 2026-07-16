from dataclasses import dataclass

import pandas as pd


@dataclass
class PortfolioPlan:
    allocations: pd.DataFrame
    invested_weight_pct: float
    cash_weight_pct: float
    risk_level: str


def build_portfolio(
    ranking: pd.DataFrame,
    asset_risk: pd.DataFrame,
    capital: float,
    profile: str = "moderado",
    min_score: float = 55.0,
    max_positions: int = 8,
    max_position_pct: float = 15.0,
    min_cash_pct: float = 20.0,
) -> PortfolioPlan:
    candidates = ranking.loc[ranking["score"] >= min_score].copy()

    if candidates.empty:
        return PortfolioPlan(
            allocations=pd.DataFrame(),
            invested_weight_pct=0.0,
            cash_weight_pct=100.0,
            risk_level="Bajo",
        )

    if "volatility_pct" in candidates.columns:
        volatility = candidates["volatility_pct"]
    elif "annual_volatility_pct" in candidates.columns:
        volatility = candidates["annual_volatility_pct"]
    elif "volatility" in candidates.columns:
        volatility = candidates["volatility"]
    else:
        risk_data = asset_risk.copy()

        if "volatility_pct" not in risk_data.columns:
            if "annual_volatility_pct" in risk_data.columns:
                risk_data["volatility_pct"] = risk_data["annual_volatility_pct"]
            elif "volatility" in risk_data.columns:
                risk_data["volatility_pct"] = risk_data["volatility"]
            else:
                risk_data["volatility_pct"] = 20.0

        volatility_map = risk_data.set_index("symbol")["volatility_pct"]

        volatility = candidates["symbol"].map(volatility_map)

    candidates["volatility_pct"] = (
        pd.to_numeric(
            volatility,
            errors="coerce",
        )
        .fillna(20.0)
        .clip(lower=1.0)
    )

    candidates = candidates.sort_values(
        ["score", "confidence"],
        ascending=False,
    ).head(max_positions)

    candidates["raw_weight"] = candidates["score"] / candidates["volatility_pct"]

    available_weight = max(0.0, 100.0 - min_cash_pct)
    raw_total = candidates["raw_weight"].sum()

    if raw_total <= 0:
        candidates["weight_pct"] = available_weight / len(candidates)
    else:
        candidates["weight_pct"] = candidates["raw_weight"] / raw_total * available_weight

    candidates["weight_pct"] = candidates["weight_pct"].clip(upper=max_position_pct)

    total_weight = candidates["weight_pct"].sum()

    if total_weight > available_weight and total_weight > 0:
        candidates["weight_pct"] *= available_weight / total_weight

    invested_weight_pct = float(candidates["weight_pct"].sum())
    cash_weight_pct = max(
        0.0,
        100.0 - invested_weight_pct,
    )

    candidates["amount_eur"] = candidates["weight_pct"] / 100 * capital

    allocations = candidates[
        [
            "symbol",
            "score",
            "confidence",
            "volatility_pct",
            "weight_pct",
            "amount_eur",
        ]
    ].reset_index(drop=True)

    risk_levels = {
        "conservador": "Bajo",
        "moderado": "Medio",
        "agresivo": "Alto",
    }

    return PortfolioPlan(
        allocations=allocations,
        invested_weight_pct=invested_weight_pct,
        cash_weight_pct=cash_weight_pct,
        risk_level=risk_levels.get(profile, "Medio"),
    )


def portfolio_equity_curve(
    prices: pd.DataFrame,
    allocations: pd.DataFrame,
    capital: float,
) -> pd.DataFrame:
    if allocations.empty or prices.empty:
        return pd.DataFrame()

    symbols = [symbol for symbol in allocations["symbol"] if symbol in prices.columns]

    if not symbols:
        return pd.DataFrame()

    normalized = prices[symbols].ffill().dropna()

    if normalized.empty:
        return pd.DataFrame()

    normalized = normalized / normalized.iloc[0]

    weights = allocations.set_index("symbol")["weight_pct"].to_dict()

    portfolio = pd.Series(
        0.0,
        index=normalized.index,
    )

    for symbol in symbols:
        portfolio += normalized[symbol] * weights[symbol] / 100 * capital

    cash_pct = max(
        0.0,
        100.0 - allocations["weight_pct"].sum(),
    )
    portfolio += capital * cash_pct / 100

    result = pd.DataFrame({"portfolio": portfolio})

    if "SPY" in prices.columns:
        spy = prices["SPY"].ffill().dropna()

        if not spy.empty:
            result["SPY"] = (spy / spy.iloc[0] * capital).reindex(result.index).ffill()

    return result
