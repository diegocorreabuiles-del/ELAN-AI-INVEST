import pandas as pd


def calculate_momentum(data: pd.DataFrame):

    close = data["Close"]

    r1 = (close.iloc[-1] / close.iloc[-21] - 1) * 100
    r3 = (close.iloc[-1] / close.iloc[-63] - 1) * 100
    r6 = (close.iloc[-1] / close.iloc[-126] - 1) * 100

    score = max(0, min(100, (r1 * 0.2 + r3 * 0.3 + r6 * 0.5) + 50))

    return {
        "1m": round(r1, 2),
        "3m": round(r3, 2),
        "6m": round(r6, 2),
        "score": round(score, 1),
    }