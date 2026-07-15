from dataclasses import dataclass
from enum import Enum


class DecisionType(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    WAIT = "WAIT"
    REDUCE = "REDUCE"
    SELL = "SELL"


@dataclass
class TrendResult:
    score: float
    confidence: float


@dataclass
class MomentumResult:
    score: float
    confidence: float


@dataclass
class RiskResult:
    score: float
    confidence: float


@dataclass
class MarketResult:
    regime: str
    confidence: float


@dataclass
class Decision:
    action: DecisionType
    score: float
    confidence: float
    explanation: str