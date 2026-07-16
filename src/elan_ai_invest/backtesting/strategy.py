import pandas as pd


def run_strategy(prices: pd.Series, signals: pd.Series) -> pd.Series:
    returns = prices.astype(float).pct_change().fillna(0.0)
    position = signals.reindex(prices.index).shift(1).fillna(0.0)
    return (1.0 + returns * position).cumprod()
