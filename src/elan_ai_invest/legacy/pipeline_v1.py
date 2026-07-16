"""Legacy analysis pipeline preserved behind ``core.pipeline`` compatibility."""

import warnings

import pandas as pd

from elan_ai_invest.decision.engine import DecisionEngine
from elan_ai_invest.indicators.engine import IndicatorEngine
from elan_ai_invest.intelligence.engine import IntelligenceEngine
from elan_ai_invest.intelligence.models import (
    MarketResult,
    MomentumResult,
    RiskResult,
    TrendResult,
)
from elan_ai_invest.market.providers import ProviderManager


class InvestmentPipeline:
    def __init__(self, provider=None):
        warnings.warn(
            "InvestmentPipeline is legacy; use elan_ai_invest.core.CoreEngine",
            DeprecationWarning,
            stacklevel=2,
        )
        self.provider = provider or ProviderManager()
        self.intelligence = IntelligenceEngine()
        self.decision_engine = DecisionEngine()

    def analyze_symbol(self, symbol: str, period: str = "2y") -> dict:
        data = self.provider.get_data(symbol, period)

        if data is None or data.empty:
            raise ValueError(f"Sin datos para {symbol}")

        indicators = IndicatorEngine(data).calculate_all()

        trend_data = indicators["trend"]
        momentum_data = indicators["momentum"]
        volatility_data = indicators["volatility"]

        trend = TrendResult(
            score=float(trend_data["score"]),
            confidence=80.0,
        )

        momentum = MomentumResult(
            score=float(momentum_data["score"]),
            confidence=75.0,
        )

        risk = RiskResult(
            score=float(volatility_data["score"]),
            confidence=75.0,
        )

        market = MarketResult(
            regime="RISK_ON" if trend.score >= 70 else "NEUTRAL",
            confidence=75.0,
        )

        decision = self.intelligence.analyze(
            trend=trend,
            momentum=momentum,
            risk=risk,
            market=market,
        )

        return {
            "symbol": symbol,
            "score": decision.score,
            "confidence": decision.confidence,
            "action": decision.action.value,
            "explanation": decision.explanation,
            "trend_score": trend.score,
            "momentum_score": momentum.score,
            "risk_score": risk.score,
        }

    def analyze_universe(
        self,
        symbols: list[str],
        period: str = "2y",
    ) -> pd.DataFrame:
        results = []

        for symbol in symbols:
            try:
                results.append(self.analyze_symbol(symbol, period))
            except Exception:
                continue

        return pd.DataFrame(results)

    def build_portfolio(self, ranking: pd.DataFrame) -> pd.DataFrame:
        return self.decision_engine.build_portfolio(ranking)
