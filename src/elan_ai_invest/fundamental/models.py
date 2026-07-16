from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FundamentalSnapshot:
    symbol: str
    company_name: str
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    peg_ratio: float | None = None
    price_to_book: float | None = None
    enterprise_to_ebitda: float | None = None
    return_on_equity: float | None = None
    return_on_assets: float | None = None
    profit_margin: float | None = None
    operating_margin: float | None = None
    revenue_growth: float | None = None
    earnings_growth: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    free_cash_flow: float | None = None
    operating_cash_flow: float | None = None
    dividend_yield: float | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FundamentalAnalysis:
    symbol: str
    score: float
    quality_score: float
    growth_score: float
    valuation_score: float
    balance_sheet_score: float
    cash_flow_score: float
    confidence: float
    decision: str
    explanation: str
    snapshot: FundamentalSnapshot
