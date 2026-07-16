from .models import MarketResult, MomentumResult, RiskResult, TrendResult


def calculate_confidence(
    trend: TrendResult,
    momentum: MomentumResult,
    risk: RiskResult,
    market: MarketResult,
) -> float:
    return round(
        (trend.confidence + momentum.confidence + risk.confidence + market.confidence) / 4,
        1,
    )
