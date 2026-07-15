import pandas as pd

from .trend import calculate_trend
from .momentum import calculate_momentum
from .volatility import calculate_volatility


class IndicatorEngine:

    def __init__(self, data: pd.DataFrame):
        self.data = data

    def calculate_all(self):

        return {
            "trend": calculate_trend(self.data),
            "momentum": calculate_momentum(self.data),
            "volatility": calculate_volatility(self.data),
        }