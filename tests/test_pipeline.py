import numpy as np
import pandas as pd

from elan_ai_invest.core.pipeline import InvestmentPipeline


class FakeProvider:

    def get_data(self, symbol, period="2y"):
        n = 300

        return pd.DataFrame(
            {
                "Open": np.linspace(100, 200, n),
                "High": np.linspace(101, 201, n),
                "Low": np.linspace(99, 199, n),
                "Close": np.linspace(100, 200, n),
                "Volume": np.full(n, 1000),
            }
        )


def test_pipeline_analyzes_symbol():
    pipeline = InvestmentPipeline(provider=FakeProvider())

    result = pipeline.analyze_symbol("TEST")

    assert result["symbol"] == "TEST"
    assert 0 <= result["score"] <= 100
    assert result["action"] in {
        "BUY",
        "HOLD",
        "WAIT",
        "REDUCE",
        "SELL",
    }


def test_pipeline_analyzes_universe():
    pipeline = InvestmentPipeline(provider=FakeProvider())

    ranking = pipeline.analyze_universe(
        ["AAA", "BBB", "CCC"]
    )

    assert len(ranking) == 3
    assert "score" in ranking.columns
    assert "confidence" in ranking.columns