def apply_constraints(
    ranking,
    max_weight=0.15,
    min_score=70,
):

    ranking = ranking.copy()

    ranking = ranking[
        ranking["score"] >= min_score
    ]

    ranking["weight"] = ranking["weight"].clip(upper=max_weight)

    total = ranking["weight"].sum()

    if total > 0:
        ranking["weight"] = ranking["weight"] / total

    return ranking