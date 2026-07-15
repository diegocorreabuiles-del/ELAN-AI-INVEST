import pandas as pd


def apply_costs(
    returns: pd.Series,
    commission=0.001,
):

    return returns - commission