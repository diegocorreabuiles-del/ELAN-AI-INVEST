from elan_ai_invest.indicators.engine import IndicatorEngine
import pandas as pd
import numpy as np


def test_indicator_engine():

    n = 300

    data = pd.DataFrame(
        {
            "Close": np.linspace(100, 200, n)
        }
    )

    engine = IndicatorEngine(data)

    result = engine.calculate_all()

    assert "trend" in result
    assert "momentum" in result
    assert "volatility" in result