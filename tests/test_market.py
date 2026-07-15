import pandas as pd

from elan_ai_invest.market.validator import validate_market_data


def test_market_validator():

    df = pd.DataFrame(
        {
            "Open": [1],
            "High": [1],
            "Low": [1],
            "Close": [1],
            "Volume": [100],
        }
    )

    assert validate_market_data(df)