from __future__ import annotations


class MarketLoader:
    def download(self, symbol: str, period: str = "2y"):
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError(
                "Falta yfinance. Ejecuta update.bat antes de descargar mercado."
            ) from exc

        return yf.download(
            symbol,
            period=period,
            auto_adjust=True,
            progress=False,
        )
