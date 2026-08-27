import pandas as pd


def calculate_weights(ranking: pd.DataFrame) -> pd.DataFrame:
    ranking = ranking.copy()
    total = float(ranking["score"].sum())
    ranking["weight"] = ranking["score"] / total if total > 0 else 0.0
    return ranking
