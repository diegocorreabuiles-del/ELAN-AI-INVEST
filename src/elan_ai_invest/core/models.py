from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd


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
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def successful_symbols(self) -> int:
        return len(self.prices.columns)
