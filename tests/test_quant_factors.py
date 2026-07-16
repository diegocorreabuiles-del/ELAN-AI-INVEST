import numpy as np
import pandas as pd

from elan_ai_invest.quant import calculate_factor_table, decision_from_score, explain_row


def _prices() -> pd.DataFrame:
    n = 320
    return pd.DataFrame(
        {
            "SPY": np.linspace(100, 150, n),
            "AAA": np.linspace(100, 190, n),
            "BBB": np.linspace(120, 105, n),
        }
    )


def test_factor_table_contains_professional_factors():
    factors = calculate_factor_table(_prices(), benchmark="SPY")
    assert set(["trend_factor", "relative_strength_factor", "risk_adjusted_factor"]).issubset(
        factors.columns
    )
    aaa = factors.loc[factors["symbol"] == "AAA"].iloc[0]
    bbb = factors.loc[factors["symbol"] == "BBB"].iloc[0]
    assert aaa["relative_strength_factor"] > bbb["relative_strength_factor"]


def test_professional_decision_and_explanation():
    assert decision_from_score(90) == "COMPRAR"
    explanation = explain_row(
        pd.Series(
            {
                "trend_factor": 90,
                "relative_strength_factor": 80,
                "risk_adjusted_factor": 75,
                "trend_quality_factor": 70,
                "volatility_pct": 18,
            }
        )
    )
    assert "tendencia" in explanation.lower()
