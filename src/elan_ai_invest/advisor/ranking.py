def rank_assets(ranking):

    return ranking.sort_values(
        "score",
        ascending=False,
    ).reset_index(drop=True)
