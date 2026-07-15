def calculate_weights(ranking):

    ranking = ranking.copy()

    total = ranking["score"].sum()

    ranking["weight"] = ranking["score"] / total

    return ranking