import yfinance as yf


class MarketLoader:

    def download(self, symbol: str, period="2y"):

        data = yf.download(
            symbol,
            period=period,
            auto_adjust=True,
            progress=False,
        )

        return data