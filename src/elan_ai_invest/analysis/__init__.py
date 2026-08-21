"""Canonical contracts for asset-level decision analysis."""

from .classification import classify_asset
from .crypto import (
    calculate_crypto_metrics,
    calculate_meme_coin_metrics,
    calculate_stablecoin_metrics,
)
from .data_confidence import calculate_data_confidence
from .decision import DEFAULT_DECISION_POLICY, DecisionPolicy, decide
from .models import (
    AssetAnalysis,
    AssetProfile,
    AssetType,
    CryptoMetrics,
    DataConfidence,
    DecisionAction,
    DecisionResult,
    DepegRisk,
    FundamentalMetrics,
    InstitutionalMetrics,
    MarketMetrics,
    MemeCoinMetrics,
    RiskMetrics,
    ScoreBreakdown,
    SentimentMetrics,
    StablecoinMetrics,
    TechnicalMetrics,
    TradePlan,
)
from .pipeline import build_asset_analysis
from .risk_engine import calculate_risk_metrics, consecutive_returns
from .score_engine import calculate_score_breakdown, weighted_score
from .technical import calculate_market_metrics, calculate_technical_metrics
from .trade_plan import calculate_trade_plan
from .weights import ASSET_SCORE_WEIGHTS, ScoreComponent, weights_for_asset

__all__ = [
    "ASSET_SCORE_WEIGHTS",
    "DEFAULT_DECISION_POLICY",
    "AssetAnalysis",
    "AssetProfile",
    "AssetType",
    "CryptoMetrics",
    "DataConfidence",
    "DepegRisk",
    "DecisionAction",
    "DecisionPolicy",
    "DecisionResult",
    "FundamentalMetrics",
    "InstitutionalMetrics",
    "MarketMetrics",
    "MemeCoinMetrics",
    "RiskMetrics",
    "ScoreBreakdown",
    "SentimentMetrics",
    "StablecoinMetrics",
    "TechnicalMetrics",
    "TradePlan",
    "ScoreComponent",
    "build_asset_analysis",
    "calculate_crypto_metrics",
    "calculate_data_confidence",
    "calculate_meme_coin_metrics",
    "calculate_stablecoin_metrics",
    "calculate_market_metrics",
    "calculate_risk_metrics",
    "calculate_score_breakdown",
    "calculate_technical_metrics",
    "calculate_trade_plan",
    "classify_asset",
    "consecutive_returns",
    "decide",
    "weighted_score",
    "weights_for_asset",
]
