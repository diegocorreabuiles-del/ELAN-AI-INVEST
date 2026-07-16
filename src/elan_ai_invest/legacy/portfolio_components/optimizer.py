import pandas as pd


class PortfolioOptimizer:

    def __init__(self, capital: float):
        self.capital = capital

    def optimize(self, ranking: pd.DataFrame):

        top = ranking.sort_values("score", ascending=False).head(8).copy()

        weight = 1 / len(top)

        top["weight"] = weight
        top["investment"] = top["weight"] * self.capital

        return top
