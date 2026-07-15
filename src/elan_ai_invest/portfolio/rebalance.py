import pandas as pd


def rebalance(portfolio: pd.DataFrame, target_weights: dict):

    portfolio = portfolio.copy()

    portfolio["target_weight"] = portfolio["symbol"].map(target_weights)

    portfolio["rebalance"] = (
        portfolio["target_weight"] - portfolio["weight"]
    )

    return portfolio