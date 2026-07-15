def filter_assets(ranking):

    return ranking[
        (ranking["score"] >= 70)
        & (ranking["confidence"] >= 70)
    ].copy()