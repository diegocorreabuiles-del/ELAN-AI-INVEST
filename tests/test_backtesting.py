import numpy as np
import pandas as pd

from elan_ai_invest.backtesting.engine import BacktestEngine


def test_backtest():

    prices = pd.Series(
        np.linspace(100, 150, 250)
    )

    signals = pd.Series(
        np.ones(250)
    )

    engine = BacktestEngine()

    report = engine.run(
        prices,
        signals,
    )

    assert "metrics" in report
    assert "equity" in report