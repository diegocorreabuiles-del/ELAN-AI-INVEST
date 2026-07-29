from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import pandas as pd


class MarketDataQualityStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STALE = "stale"
    INSUFFICIENT = "insufficient"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class MarketDataAssetQuality:
    symbol: str
    status: MarketDataQualityStatus
    source: str
    observations: int
    expected_sessions: int
    missing_sessions: int
    coverage_ratio: float
    first_observation: datetime | None
    last_observation: datetime | None
    age_days: int | None


@dataclass(frozen=True)
class MarketDataQualityReport:
    provider: str
    status: MarketDataQualityStatus
    assets: dict[str, MarketDataAssetQuality]
    generated_at: datetime

    @property
    def issue_count(self) -> int:
        return sum(
            quality.status is not MarketDataQualityStatus.HEALTHY
            for quality in self.assets.values()
        )

    @property
    def average_coverage_ratio(self) -> float:
        available = [item.coverage_ratio for item in self.assets.values() if item.observations]
        return sum(available) / len(available) if available else 0.0


@dataclass
class DownloadResult:
    prices: pd.DataFrame
    errors: dict[str, str]
    quality: MarketDataQualityReport | None = None


class MarketDataProvider(ABC):
    @abstractmethod
    def download_prices(
        self,
        symbols: Iterable[str],
        period: str,
        interval: str = "1d",
        minimum_history: int = 60,
    ) -> DownloadResult:
        raise NotImplementedError
