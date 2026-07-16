import pandas as pd


def calculate_trend(data: pd.DataFrame) -> dict[str, float]:
    close = data["Close"].astype(float).dropna()
    if len(close) < 20:
        return {"ema20": 0.0, "ema50": 0.0, "ema200": 0.0, "score": 0.0}
    ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
    ema200 = close.ewm(span=200, adjust=False).mean().iloc[-1]
    score = 0.0
    if close.iloc[-1] > ema20:
        score += 25
    if ema20 > ema50:
        score += 30
    if ema50 > ema200:
        score += 30
    if close.iloc[-1] > ema200:
        score += 15
    return {"ema20": round(float(ema20), 2), "ema50": round(float(ema50), 2), "ema200": round(float(ema200), 2), "score": score}
