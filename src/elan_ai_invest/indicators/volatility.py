import pandas as pd
import numpy as np


def calculate_volatility(data: pd.DataFrame):

    returns = data["Close"].pct_change().dropna()

    vol = returns.std() * np.sqrt(252) * 100

    score = max(0, 100 - vol)

    return {
        "volatility": round(vol, 2),
        "score": round(score, 1),
    }