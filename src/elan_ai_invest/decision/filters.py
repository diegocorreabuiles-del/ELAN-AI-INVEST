def filter_assets(ranking):
    required = {"score", "confidence"}
    if ranking.empty or not required.issubset(ranking.columns):
        return ranking.iloc[0:0].copy()
    return ranking[(ranking["score"] >= 70) & (ranking["confidence"] >= 65)].copy()
