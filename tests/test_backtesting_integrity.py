import numpy as np
import pandas as pd
import pytest

from elan_ai_invest.backtesting import BacktestEngine
from elan_ai_invest.backtesting.costs import apply_transaction_costs


def test_transaction_costs_apply_only_when_weights_change():
    index = pd.date_range("2025-01-01", periods=4, freq="D")
    weights = pd.DataFrame(
        {"AAA": [0.0, 1.0, 1.0, 0.0], "BBB": [0.0, 0.0, 0.0, 1.0]},
        index=index,
    )
    gross_returns = pd.Series(0.0, index=index)

    net_returns, costs, turnover = apply_transaction_costs(
        gross_returns,
        weights,
        commission_pct=0.10,
        slippage_pct=0.05,
    )

    np.testing.assert_allclose(turnover, [0.0, 1.0, 0.0, 2.0])
    np.testing.assert_allclose(costs, [0.0, 0.0015, 0.0, 0.0030])
    np.testing.assert_allclose(net_returns, -costs)


def test_momentum_signal_is_executed_one_bar_later():
    index = pd.date_range("2025-01-01", periods=50, freq="D")
    prices = pd.DataFrame(
        {
            "AAA": [100.0] * 21 + [200.0] * 29,
            "SPY": [100.0] * 50,
        },
        index=index,
    )

    result = BacktestEngine().run_momentum(
        prices,
        lookback=21,
        top_n=1,
        rebalance=5,
        benchmark_symbol="SPY",
    )

    assert result.loc[index[21], "strategy"] == pytest.approx(1.0)
    assert result.loc[index[21], "turnover"] == pytest.approx(0.0)
    assert result.loc[index[22], "turnover"] == pytest.approx(1.0)
    assert result["strategy"].iloc[-1] == pytest.approx(1.0)


def test_configured_benchmark_uses_its_own_price_series():
    index = pd.date_range("2025-01-01", periods=60, freq="D")
    prices = pd.DataFrame(
        {
            "AAA": np.linspace(100.0, 160.0, len(index)),
            "SPY": np.linspace(200.0, 150.0, len(index)),
        },
        index=index,
    )

    result = BacktestEngine().run_momentum(
        prices,
        lookback=21,
        top_n=1,
        rebalance=5,
        benchmark_symbol="SPY",
    )
    expected = (1.0 + prices["SPY"].pct_change().fillna(0.0)).cumprod()

    pd.testing.assert_series_equal(result["benchmark"], expected, check_names=False)
    assert result.attrs["benchmark_symbol"] == "SPY"


def test_missing_configured_benchmark_fails_clearly():
    prices = pd.DataFrame(
        {"AAA": np.linspace(100.0, 160.0, 60)},
        index=pd.date_range("2025-01-01", periods=60, freq="D"),
    )

    with pytest.raises(ValueError, match="benchmark.*SPY.*no está disponible"):
        BacktestEngine().run_momentum(prices, benchmark_symbol="SPY")


def test_costs_reduce_net_equity_and_are_reported():
    prices = pd.DataFrame(
        {
            "AAA": np.linspace(100.0, 180.0, 80),
            "SPY": np.linspace(100.0, 120.0, 80),
        },
        index=pd.date_range("2025-01-01", periods=80, freq="D"),
    )

    result = BacktestEngine().run_momentum(
        prices,
        lookback=21,
        top_n=1,
        rebalance=5,
        commission_pct=0.10,
        slippage_pct=0.05,
        benchmark_symbol="SPY",
    )

    assert result["transaction_cost"].sum() > 0
    assert result["strategy"].iloc[-1] < result["strategy_gross"].iloc[-1]
