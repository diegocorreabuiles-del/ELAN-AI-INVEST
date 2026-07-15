def build_recommendation(ranking, portfolio):

    best = ranking.iloc[0]

    return {
        "symbol": best["symbol"],
        "score": best["score"],
        "action": "BUY",
    }