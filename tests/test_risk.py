import numpy as np
import pandas as pd
import pytest

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


def test_missing_prices_are_excluded_instead_of_becoming_zero_returns():
    prices = sample_prices()
    missing_date = prices.index[100]
    following_date = prices.index[101]
    prices.loc[missing_date, "BBB"] = np.nan

    report = calculate_risk_report(prices)

    assert missing_date not in report.daily_returns.index
    assert following_date not in report.daily_returns.index
    assert len(report.daily_returns) == len(prices) - 3


def test_risk_requires_enough_aligned_consecutive_sessions():
    prices = sample_prices().iloc[:80].copy()
    prices.loc[prices.index[10:40], "BBB"] = np.nan

    with pytest.raises(ValueError, match="60 sesiones alineadas"):
        calculate_risk_report(prices)
