from __future__ import annotations

import math
from collections.abc import Mapping

from .models import (
    AssetProfile,
    FundamentalMetrics,
    InstitutionalMetrics,
    RiskMetrics,
    ScoreBreakdown,
    SentimentMetrics,
    StablecoinMetrics,
    TechnicalMetrics,
)
from .weights import ScoreComponent, weights_for_asset


def weighted_score(
    components: Mapping[ScoreComponent, float | None],
    weights: Mapping[ScoreComponent, float],
) -> float | None:
    """Return a normalized score using only components with actual data."""

    available = {
        component: float(value)
        for component, value in components.items()
        if component in weights and value is not None
    }
    if not available:
        return None
    for component, value in available.items():
        if not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError(f"{component.value} debe estar entre 0 y 100")
    available_weight = sum(weights[component] for component in available)
    if available_weight <= 0:
        return None
    return (
        sum(available[component] * weights[component] for component in available) / available_weight
    )


def calculate_score_breakdown(
    profile: AssetProfile,
    *,
    technical: TechnicalMetrics | None = None,
    fundamental: FundamentalMetrics | None = None,
    sentiment: SentimentMetrics | None = None,
    institutional: InstitutionalMetrics | None = None,
    risk: RiskMetrics | None = None,
    stablecoin: StablecoinMetrics | None = None,
) -> ScoreBreakdown:
    """Calculate conviction without inventing unavailable components."""

    components = {
        ScoreComponent.TECHNICAL: technical.score if technical else None,
        ScoreComponent.FUNDAMENTAL: fundamental.score if fundamental else None,
        ScoreComponent.SENTIMENT: sentiment.score if sentiment else None,
        ScoreComponent.INSTITUTIONAL: institutional.score if institutional else None,
        ScoreComponent.RISK: risk.score if risk else None,
        ScoreComponent.PEG_HEALTH: stablecoin.peg_health_score if stablecoin else None,
        ScoreComponent.LIQUIDITY: stablecoin.liquidity_health_score if stablecoin else None,
        ScoreComponent.ISSUER_RISK: stablecoin.issuer_risk_score if stablecoin else None,
        ScoreComponent.ADOPTION: stablecoin.adoption_trend_score if stablecoin else None,
    }
    permitted = weights_for_asset(profile.asset_type)
    conviction = weighted_score(components, permitted)

    def value(component: ScoreComponent) -> float | None:
        return components[component] if component in permitted else None

    return ScoreBreakdown(
        conviction=conviction,
        technical=value(ScoreComponent.TECHNICAL),
        fundamental=value(ScoreComponent.FUNDAMENTAL),
        sentiment=value(ScoreComponent.SENTIMENT),
        institutional=value(ScoreComponent.INSTITUTIONAL),
        risk=value(ScoreComponent.RISK),
        peg_health=value(ScoreComponent.PEG_HEALTH),
        liquidity=value(ScoreComponent.LIQUIDITY),
        issuer_risk=value(ScoreComponent.ISSUER_RISK),
        adoption=value(ScoreComponent.ADOPTION),
    )
