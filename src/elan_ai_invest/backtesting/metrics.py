import numpy as np
import pandas as pd


def calculate_metrics(equity: pd.Series) -> dict[str, float]:
    returns = equity.pct_change().dropna()
    if equity.empty or returns.empty:
        return {"return": 0.0, "annual_return": 0.0, "volatility": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}
    total_return = (equity.iloc[-1] / equity.iloc[0] - 1) * 100
    annual_return = ((equity.iloc[-1] / equity.iloc[0]) ** (252 / max(len(equity), 1)) - 1) * 100
    volatility = returns.std() * np.sqrt(252) * 100
    sharpe = annual_return / volatility if volatility > 0 else 0.0
    drawdown = (equity / equity.cummax() - 1).min() * 100
    return {"return": round(float(total_return), 2), "annual_return": round(float(annual_return), 2), "volatility": round(float(volatility), 2), "sharpe": round(float(sharpe), 2), "max_drawdown": round(float(drawdown), 2)}
