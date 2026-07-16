import numpy as np
import pandas as pd

from elan_ai_invest.institutional import optimize_portfolio


def _prices():
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0005, [0.01, 0.015, 0.02], size=(400, 3))
    return pd.DataFrame((1 + returns).cumprod(axis=0) * 100, columns=["AAA", "BBB", "CCC"])


def test_risk_parity_weights_are_valid():
    result = optimize_portfolio(_prices(), method="risk_parity", max_weight=0.5)
    assert abs(result.weights.sum() - 1) < 1e-9
    assert result.weights.max() <= 0.500001
    assert result.annual_volatility_pct > 0


def test_minimum_variance_weights_are_valid():
    result = optimize_portfolio(_prices(), method="minimum_variance", max_weight=0.6)
    assert abs(result.weights.sum() - 1) < 1e-9
    assert (result.weights >= 0).all()
