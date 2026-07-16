import numpy as np
import pandas as pd

from elan_ai_invest.backtesting import BacktestEngine


def test_backtesting_engine():
    prices = pd.Series(np.linspace(100, 150, 250))
    signals = pd.Series(np.ones(250))
    report = BacktestEngine().run(prices, signals)
    assert "metrics" in report and "equity" in report
