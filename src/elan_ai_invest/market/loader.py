from __future__ import annotations

import pandas as pd


class MarketLoader:
    def download(self, symbol: str, period: str = "2y") -> pd.DataFrame:
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
