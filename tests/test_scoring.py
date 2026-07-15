import numpy as np
import pandas as pd

from elan_ai_invest.scoring import score_assets


def test_scoring_returns_ranked_rows():
    idx = pd.date_range("2024-01-01", periods=260, freq="B")
    prices = pd.DataFrame({
        "UP": np.linspace(100, 160, len(idx)),
        "DOWN": np.linspace(160, 100, len(idx)),
    }, index=idx)
    result = score_assets(prices)
    assert list(result.columns)
    assert result.iloc[0]["symbol"] == "UP"
    assert 0 <= result.iloc[0]["score"] <= 100
