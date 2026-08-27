import pandas as pd


def allocate_capital(portfolio: pd.DataFrame, capital: float) -> pd.DataFrame:

    portfolio = portfolio.copy()

    portfolio["investment"] = portfolio["weight"] * capital

    return portfolio
