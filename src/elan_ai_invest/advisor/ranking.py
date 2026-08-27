import pandas as pd


def rank_assets(ranking: pd.DataFrame) -> pd.DataFrame:

    return ranking.sort_values(
        "score",
        ascending=False,
    ).reset_index(drop=True)
