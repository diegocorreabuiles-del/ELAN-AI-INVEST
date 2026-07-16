from pathlib import Path

from elan_ai_invest.backtest import momentum_backtest as compatibility_momentum_backtest
from elan_ai_invest.backtesting import momentum_backtest
from elan_ai_invest.core import CoreEngine
from elan_ai_invest.core.engine import CoreEngine as EngineImplementation
from elan_ai_invest.core.pipeline import InvestmentPipeline
from elan_ai_invest.portfolio import PortfolioPlan, build_portfolio


def test_core_engine_is_the_canonical_pipeline():
    assert CoreEngine is EngineImplementation
    assert InvestmentPipeline.__module__ == "elan_ai_invest.legacy.pipeline_v1"


def test_portfolio_package_resolves_to_the_canonical_engine():
    package_root = Path(__file__).resolve().parents[1] / "src" / "elan_ai_invest"

    assert not (package_root / "portfolio.py").exists()
    assert PortfolioPlan.__module__ == "elan_ai_invest.portfolio.engine"
    assert build_portfolio.__module__ == "elan_ai_invest.portfolio.engine"
    assert (package_root / "legacy" / "portfolio_package_v1.py").exists()


def test_backtest_compatibility_path_delegates_to_canonical_package():
    assert compatibility_momentum_backtest is momentum_backtest


def test_momentum_adapter_delegates_to_canonical_backtest_engine():
    import pandas as pd

    from elan_ai_invest.backtesting import BacktestEngine

    prices = pd.DataFrame(
        {"AAA": range(100, 200), "BBB": range(200, 300)},
        index=pd.date_range("2025-01-01", periods=100, freq="D"),
    )

    expected = BacktestEngine().run_momentum(prices, lookback=21, top_n=1, rebalance=5)
    actual = momentum_backtest(prices, lookback=21, top_n=1, rebalance=5)
    pd.testing.assert_frame_equal(actual, expected)
