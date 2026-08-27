import pandas as pd


def apply_constraints(
    ranking: pd.DataFrame,
    max_weight: float = 0.15,
) -> pd.DataFrame:
    ranking = ranking.copy()
    if ranking.empty:
        return ranking
    ranking["weight"] = ranking["weight"].clip(upper=max_weight)
    return ranking
