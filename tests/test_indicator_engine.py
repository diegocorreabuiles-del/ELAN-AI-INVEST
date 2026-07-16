import numpy as np
import pandas as pd

from elan_ai_invest.indicators import IndicatorEngine


def test_indicator_engine():
    n = 300
    data = pd.DataFrame({"Close": np.linspace(100, 200, n)})
    result = IndicatorEngine(data).calculate_all()
    assert set(result) == {"trend", "momentum", "volatility"}
    assert result["trend"]["score"] >= 70
