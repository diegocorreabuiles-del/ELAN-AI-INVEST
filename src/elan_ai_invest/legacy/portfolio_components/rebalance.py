from collections.abc import Mapping

import pandas as pd


def rebalance(
    portfolio: pd.DataFrame,
    target_weights: Mapping[str, float],
) -> pd.DataFrame:

    portfolio = portfolio.copy()

    portfolio["target_weight"] = portfolio["symbol"].map(target_weights)

    portfolio["rebalance"] = portfolio["target_weight"] - portfolio["weight"]

    return portfolio
