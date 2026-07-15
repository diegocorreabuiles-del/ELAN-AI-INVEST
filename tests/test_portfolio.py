import pandas as pd

from elan_ai_invest.portfolio.optimizer import PortfolioOptimizer


def test_optimizer():

    ranking = pd.DataFrame(
        {
            "symbol": ["AAA", "BBB", "CCC", "DDD"],
            "score": [90, 80, 70, 60],
        }
    )

    optimizer = PortfolioOptimizer(100000)

    portfolio = optimizer.optimize(ranking)

    assert len(portfolio) == 4
    assert round(portfolio["weight"].sum(), 2) == 1.00
    assert round(portfolio["investment"].sum(), 2) == 100000.00