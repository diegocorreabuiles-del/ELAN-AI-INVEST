from __future__ import annotations

from typing import Any

from .models import FundamentalSnapshot


_FIELD_MAP = {
    "sector": "sector",
    "industry": "industry",
    "market_cap": "marketCap",
    "trailing_pe": "trailingPE",
    "forward_pe": "forwardPE",
    "peg_ratio": "pegRatio",
    "price_to_book": "priceToBook",
    "enterprise_to_ebitda": "enterpriseToEbitda",
    "return_on_equity": "returnOnEquity",
    "return_on_assets": "returnOnAssets",
    "profit_margin": "profitMargins",
    "operating_margin": "operatingMargins",
    "revenue_growth": "revenueGrowth",
    "earnings_growth": "earningsGrowth",
    "debt_to_equity": "debtToEquity",
    "current_ratio": "currentRatio",
    "free_cash_flow": "freeCashflow",
    "operating_cash_flow": "operatingCashflow",
    "dividend_yield": "dividendYield",
}


def _value(info: dict[str, Any], key: str) -> Any:
    value = info.get(key)
    return None if value in ("", "N/A", "None") else value


class YahooFundamentalProvider:
    def get_snapshot(self, symbol: str) -> FundamentalSnapshot:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError(
                "Falta yfinance. Ejecuta update.bat antes de usar datos fundamentales."
            ) from exc

        ticker = yf.Ticker(symbol)
        try:
            info = ticker.get_info()
        except Exception:
            info = ticker.info

        values = {
            field: _value(info, source)
            for field, source in _FIELD_MAP.items()
        }

        return FundamentalSnapshot(
            symbol=symbol.upper(),
            company_name=str(info.get("longName") or info.get("shortName") or symbol.upper()),
            **values,
        )
