def allocate(ranking):

    return ranking.sort_values(
        "weight",
        ascending=False,
    ).reset_index(drop=True)