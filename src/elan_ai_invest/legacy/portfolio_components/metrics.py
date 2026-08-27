import pandas as pd


def portfolio_metrics(portfolio: pd.DataFrame) -> dict[str, float | int]:

    return {
        "positions": len(portfolio),
        "total_weight": round(portfolio["weight"].sum(), 4),
        "capital": round(portfolio["investment"].sum(), 2),
        "average_weight": round(portfolio["weight"].mean(), 4),
    }
