import numpy as np
import pandas as pd


def calculate_metrics(equity: pd.Series):

    returns = equity.pct_change().dropna()

    if len(returns) == 0:
        return {}

    total_return = (equity.iloc[-1] - 1) * 100

    annual_return = (
        equity.iloc[-1] ** (252 / len(equity)) - 1
    ) * 100

    volatility = returns.std() * np.sqrt(252) * 100

    sharpe = (
        annual_return / volatility
        if volatility > 0
        else 0
    )

    drawdown = (
        equity / equity.cummax() - 1
    ).min() * 100

    return {
        "return": round(total_return, 2),
        "annual_return": round(annual_return, 2),
        "volatility": round(volatility, 2),
        "sharpe": round(sharpe, 2),
        "max_drawdown": round(drawdown, 2),
    }