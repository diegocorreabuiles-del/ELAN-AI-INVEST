import pandas as pd


def allocate_capital(portfolio: pd.DataFrame, capital: float):

    portfolio = portfolio.copy()

    portfolio["investment"] = portfolio["weight"] * capital

    return portfolio