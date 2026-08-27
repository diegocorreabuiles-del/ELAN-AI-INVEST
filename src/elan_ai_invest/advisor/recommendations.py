import pandas as pd


def build_recommendation(
    ranking: pd.DataFrame,
    portfolio: object,
) -> dict[str, object]:
    del portfolio

    best = ranking.iloc[0]

    return {
        "symbol": best["symbol"],
        "score": best["score"],
        "action": "BUY",
    }
