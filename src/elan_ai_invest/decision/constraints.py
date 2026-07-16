def apply_constraints(ranking, max_weight: float = 0.15):
    ranking = ranking.copy()
    if ranking.empty:
        return ranking
    ranking["weight"] = ranking["weight"].clip(upper=max_weight)
    return ranking
