from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pandas as pd

from elan_ai_invest.providers.base import MarketDataQualityReport


@dataclass
class AnalysisRequest:
    symbols: list[str]
    period: str
    save_snapshot: bool = False


@dataclass
class AnalysisResult:
    prices: pd.DataFrame
    ranking: pd.DataFrame
    errors: dict[str, str]
    market_regime: str
    breadth_pct: float
    average_score: float
    quality: MarketDataQualityReport | None = None
    captured_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def successful_symbols(self) -> int:
        return len(self.prices.columns)
