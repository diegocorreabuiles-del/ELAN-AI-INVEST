from .loader import MarketLoader


class ProviderManager:

    def __init__(self):
        self.loader = MarketLoader()

    def get_data(self, symbol: str, period="2y"):
        return self.loader.download(symbol, period)