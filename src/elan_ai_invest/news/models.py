from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum


class CorporateEventType(StrEnum):
    EARNINGS = "earnings"
    DIVIDEND = "dividend"
    EX_DIVIDEND = "ex_dividend"


@dataclass(frozen=True)
class NewsItem:
    symbol: str
    title: str
    publisher: str
    url: str
    published_at: datetime
    summary: str | None = None


@dataclass(frozen=True)
class CorporateEvent:
    symbol: str
    event_type: CorporateEventType
    event_date: date
    source: str = "Yahoo Finance"


@dataclass(frozen=True)
class NewsEventsResult:
    symbol: str
    news: tuple[NewsItem, ...] = ()
    events: tuple[CorporateEvent, ...] = ()
    errors: dict[str, str] = field(default_factory=dict)
    provider: str = "Yahoo Finance"
    captured_at: datetime = field(default_factory=lambda: datetime.now(UTC))
