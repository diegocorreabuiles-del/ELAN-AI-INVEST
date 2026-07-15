import pandas as pd


def calculate_trend(data: pd.DataFrame):

    close = data["Close"]

    ema20 = close.ewm(span=20).mean().iloc[-1]
    ema50 = close.ewm(span=50).mean().iloc[-1]
    ema200 = close.ewm(span=200).mean().iloc[-1]

    score = 0

    if ema20 > ema50:
        score += 35

    if ema50 > ema200:
        score += 35

    if close.iloc[-1] > ema200:
        score += 30

    return {
        "ema20": round(ema20, 2),
        "ema50": round(ema50, 2),
        "ema200": round(ema200, 2),
        "score": score,
    }