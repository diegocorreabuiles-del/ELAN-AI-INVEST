from pathlib import Path

import numpy as np
import pandas as pd

from elan_ai_invest.core.config import Settings
from elan_ai_invest.core.engine import CoreEngine
from elan_ai_invest.core.models import AnalysisRequest
from elan_ai_invest.providers.base import DownloadResult, MarketDataProvider


class FakeProvider(MarketDataProvider):
    def download_prices(self, symbols, period):
        idx = pd.date_range("2024-01-01", periods=260, freq="B")
        prices = pd.DataFrame(
            {symbol: np.linspace(100, 150 + i, len(idx)) for i, symbol in enumerate(symbols)},
            index=idx,
        )
        return DownloadResult(prices=prices, errors={})


class NullLogger:
    def info(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


def test_core_engine_orchestrates_analysis(tmp_path: Path):
    engine = CoreEngine(Settings(), FakeProvider(), tmp_path, NullLogger())
    result = engine.run_analysis(AnalysisRequest(symbols=["SPY", "QQQ"], period="2y"))
    assert result.successful_symbols == 2
    assert not result.ranking.empty
    assert result.market_regime in {"Alcista", "Mixto", "Defensivo"}
