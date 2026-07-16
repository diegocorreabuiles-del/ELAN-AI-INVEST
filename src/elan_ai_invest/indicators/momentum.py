import pandas as pd


def calculate_momentum(data: pd.DataFrame) -> dict[str, float]:
    close = data["Close"].astype(float).dropna()
    if len(close) < 22:
        return {"1m": 0.0, "3m": 0.0, "6m": 0.0, "score": 50.0}
    def ret(days: int) -> float:
        if len(close) <= days:
            return 0.0
        return float((close.iloc[-1] / close.iloc[-days - 1] - 1) * 100)
    r1, r3, r6 = ret(21), ret(63), ret(126)
    score = max(0.0, min(100.0, 50 + r1 * 0.20 + r3 * 0.30 + r6 * 0.50))
    return {"1m": round(r1, 2), "3m": round(r3, 2), "6m": round(r6, 2), "score": round(score, 1)}
