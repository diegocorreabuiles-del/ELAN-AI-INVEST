import pandas as pd


def run_strategy(prices: pd.Series, signals: pd.Series) -> pd.Series:

    returns = prices.pct_change().fillna(0)

    position = signals.shift(1).fillna(0)

    strategy_returns = returns * position

    equity = (1 + strategy_returns).cumprod()

    return equity