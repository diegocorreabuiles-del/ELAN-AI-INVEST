from .loader import MarketLoader


class ProviderManager:
    def __init__(self):
        self.loader = MarketLoader()

    def get_data(self, symbol: str, period: str = "2y"):
        data = self.loader.download(symbol, period)
        if getattr(data.columns, "nlevels", 1) > 1:
            data.columns = data.columns.get_level_values(0)
        return data
