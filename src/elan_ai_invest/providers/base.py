from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd


@dataclass
class DownloadResult:
    prices: pd.DataFrame
    errors: dict[str, str]


class MarketDataProvider(ABC):
    @abstractmethod
    def download_prices(self, symbols: Iterable[str], period: str) -> DownloadResult:
        raise NotImplementedError
