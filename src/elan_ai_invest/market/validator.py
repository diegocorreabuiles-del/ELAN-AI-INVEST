import pandas as pd


def validate_market_data(data: pd.DataFrame) -> bool:

    required = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]

    if data.empty:
        return False

    for column in required:
        if column not in data.columns:
            return False

    return True