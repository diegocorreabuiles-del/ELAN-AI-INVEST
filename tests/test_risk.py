import numpy as np
import pandas as pd

from elan_ai_invest.risk import calculate_risk_report, suggested_position_size_pct


def sample_prices() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-01", periods=300, freq="B")
    returns = rng.normal([0.0005, 0.0003], [0.01, 0.015], size=(300, 2))
    prices = 100 * np.cumprod(1 + returns, axis=0)
    return pd.DataFrame(prices, index=dates, columns=["AAA", "BBB"])


def test_equal_weight_report_is_complete():
    report = calculate_risk_report(sample_prices())
    assert round(float(report.weights.sum()), 8) == 1.0
    assert report.annual_volatility_pct > 0
    assert report.var_95_pct >= 0
    assert report.cvar_95_pct >= report.var_95_pct
    assert report.correlation.shape == (2, 2)
    assert set(report.asset_risk["symbol"]) == {"AAA", "BBB"}


def test_custom_weights_are_normalised():
    report = calculate_risk_report(sample_prices(), {"AAA": 80, "BBB": 20})
    assert report.weights["AAA"] == 0.8
    assert report.weights["BBB"] == 0.2


def test_position_size_respects_cap():
    assert suggested_position_size_pct(10, max_position_pct=12) <= 12
    assert suggested_position_size_pct(0) == 0
