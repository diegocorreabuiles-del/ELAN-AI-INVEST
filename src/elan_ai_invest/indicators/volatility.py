import numpy as np
import pandas as pd


def calculate_volatility(data: pd.DataFrame) -> dict[str, float]:
    returns = data["Close"].astype(float).pct_change().dropna()
    vol = float(returns.std() * np.sqrt(252) * 100) if not returns.empty else 100.0
    return {"volatility": round(vol, 2), "score": round(max(0.0, min(100.0, 100.0 - vol)), 1)}
