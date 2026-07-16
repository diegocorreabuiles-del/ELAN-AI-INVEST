import numpy as np
import pandas as pd
import pytest

from elan_ai_invest.institutional import optimize_portfolio


def _prices(asset_count: int = 3):
    rng = np.random.default_rng(42)
    volatility = np.linspace(0.01, 0.02, asset_count)
    returns = rng.normal(0.0005, volatility, size=(400, asset_count))
    columns = [f"ASSET_{index:02d}" for index in range(asset_count)]
    return pd.DataFrame((1 + returns).cumprod(axis=0) * 100, columns=columns)


def test_risk_parity_weights_are_valid():
    result = optimize_portfolio(_prices(), method="risk_parity", max_weight=0.5)
    assert abs(result.weights.sum() - 1) < 1e-9
    assert result.weights.max() <= 0.500001
    assert result.annual_volatility_pct > 0


def test_minimum_variance_weights_are_valid():
    result = optimize_portfolio(_prices(), method="minimum_variance", max_weight=0.6)
    assert abs(result.weights.sum() - 1) < 1e-9
    assert (result.weights >= 0).all()


@pytest.mark.parametrize(
    ("asset_count", "max_weight"),
    [(1, 0.5), (3, 0.25), (4, 0.24), (10, 0.09), (12, 0.08)],
)
def test_infeasible_max_weight_fails_clearly(asset_count: int, max_weight: float):
    with pytest.raises(ValueError, match="max_weight inviable"):
        optimize_portfolio(_prices(asset_count), max_weight=max_weight)


@pytest.mark.parametrize(
    ("asset_count", "max_weight"),
    [(1, 1.0), (3, 0.34), (4, 0.25), (10, 0.1), (12, 0.1)],
)
def test_feasible_max_weight_is_always_respected(asset_count: int, max_weight: float):
    result = optimize_portfolio(_prices(asset_count), method="equal_weight", max_weight=max_weight)

    assert abs(result.weights.sum() - 1) < 1e-9
    assert result.weights.max() <= max_weight + 1e-9
