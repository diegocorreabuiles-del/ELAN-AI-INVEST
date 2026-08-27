import pandas as pd


def allocate(ranking: pd.DataFrame) -> pd.DataFrame:
    return ranking.sort_values("weight", ascending=False).reset_index(drop=True)
