from pathlib import Path

import numpy as np
import pandas as pd

from elan_ai_invest.core.config import Settings
from elan_ai_invest.core.engine import CoreEngine
from elan_ai_invest.core.models import AnalysisRequest
from elan_ai_invest.market.quality import assess_market_data_quality
from elan_ai_invest.providers.base import DownloadResult, MarketDataProvider


class FakeProvider(MarketDataProvider):
    def __init__(self):
        self.request = None
        self.quality = None

    def download_prices(self, symbols, period, interval="1d", minimum_history=60):
        self.request = {
            "symbols": list(symbols),
            "period": period,
            "interval": interval,
            "minimum_history": minimum_history,
        }
        idx = pd.date_range("2024-01-01", periods=260, freq="B")
        prices = pd.DataFrame(
            {
                symbol: np.linspace(100, 150 + i, len(idx))
                for i, symbol in enumerate(self.request["symbols"])
            },
            index=idx,
        )
        self.quality = assess_market_data_quality(
            prices,
            self.request["symbols"],
            minimum_history=minimum_history,
            provider="Fake",
            now=idx[-1] + pd.Timedelta(days=1),
        )
        return DownloadResult(prices=prices, errors={}, quality=self.quality)


class NullLogger:
    def info(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


def test_core_engine_orchestrates_analysis(tmp_path: Path):
    provider = FakeProvider()
    engine = CoreEngine(Settings(), provider, tmp_path, NullLogger())
    result = engine.run_analysis(AnalysisRequest(symbols=["SPY", "QQQ"], period="2y"))
    assert result.successful_symbols == 2
    assert not result.ranking.empty
    assert result.market_regime in {"Alcista", "Mixto", "Defensivo"}
    assert result.quality is provider.quality
    assert provider.request == {
        "symbols": ["SPY", "QQQ"],
        "period": "2y",
        "interval": "1d",
        "minimum_history": 210,
    }
