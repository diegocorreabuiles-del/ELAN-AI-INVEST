import pandas as pd


def validate_market_data(data: pd.DataFrame) -> bool:
    return not data.empty and {"Open", "High", "Low", "Close", "Volume"}.issubset(data.columns)
