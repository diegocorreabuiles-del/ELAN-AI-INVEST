from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, date, datetime
from numbers import Real
from typing import Any, Protocol
from urllib.parse import urlsplit

from .models import CorporateEvent, CorporateEventType, NewsEventsResult, NewsItem

LOGGER = logging.getLogger("elan_ai_invest.news")
_NEWS_ERROR = "Noticias temporalmente no disponibles."
_EVENTS_ERROR = "Calendario corporativo temporalmente no disponible."


class NewsEventsProvider(Protocol):
    def fetch(self, symbol: str, max_items: int = 10) -> NewsEventsResult: ...


def _nested_value(payload: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = payload
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _first_value(payload: Mapping[str, Any], *paths: tuple[str, ...]) -> Any:
    for path in paths:
        value = _nested_value(payload, path)
        if value not in (None, ""):
            return value
    return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_datetime(value: Any) -> datetime | None:
    parsed: datetime
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, datetime.min.time(), tzinfo=UTC)
    elif isinstance(value, Real) and not isinstance(value, bool):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        try:
            parsed = datetime.fromtimestamp(timestamp, tz=UTC)
        except (OSError, OverflowError, ValueError):
            return None
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.replace(".", "", 1).isdigit():
            return _parse_datetime(float(text))
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _safe_url(value: Any) -> str | None:
    url = _clean_text(value)
    if url is None:
        return None
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    return url


def _normalise_news_item(raw: Any, symbol: str) -> NewsItem | None:
    if not isinstance(raw, Mapping):
        return None
    title = _clean_text(_first_value(raw, ("content", "title"), ("title",)))
    publisher = _clean_text(
        _first_value(
            raw,
            ("content", "provider", "displayName"),
            ("publisher",),
        )
    )
    url = _safe_url(
        _first_value(
            raw,
            ("content", "canonicalUrl", "url"),
            ("content", "clickThroughUrl", "url"),
            ("link",),
        )
    )
    published_at = _parse_datetime(
        _first_value(
            raw,
            ("content", "pubDate"),
            ("providerPublishTime",),
            ("pubDate",),
        )
    )
    summary = _clean_text(_first_value(raw, ("content", "summary"), ("summary",)))
    if title is None or url is None or published_at is None:
        return None
    return NewsItem(
        symbol=symbol,
        title=title,
        publisher=publisher or "Yahoo Finance",
        url=url,
        published_at=published_at,
        summary=summary,
    )


def normalise_news(raw_items: Any, symbol: str, max_items: int) -> tuple[NewsItem, ...]:
    if not isinstance(raw_items, Iterable) or isinstance(raw_items, (str, bytes, Mapping)):
        return ()
    items = [item for raw in raw_items if (item := _normalise_news_item(raw, symbol)) is not None]
    items.sort(key=lambda item: item.published_at, reverse=True)

    deduplicated: list[NewsItem] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    for item in items:
        url_key = item.url.casefold()
        title_key = " ".join(item.title.casefold().split())
        if url_key in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url_key)
        seen_titles.add(title_key)
        deduplicated.append(item)
        if len(deduplicated) >= max_items:
            break
    return tuple(deduplicated)


def _event_dates(value: Any) -> tuple[date, ...]:
    values = value if isinstance(value, (list, tuple, set)) else (value,)
    parsed_dates: list[date] = []
    for item in values:
        parsed = _parse_datetime(item)
        if parsed is not None:
            parsed_dates.append(parsed.date())
    return tuple(parsed_dates)


def normalise_calendar(
    raw_calendar: Any,
    symbol: str,
    *,
    today: date,
) -> tuple[CorporateEvent, ...]:
    if not isinstance(raw_calendar, Mapping):
        return ()
    fields = (
        ("Earnings Date", CorporateEventType.EARNINGS),
        ("Dividend Date", CorporateEventType.DIVIDEND),
        ("Ex-Dividend Date", CorporateEventType.EX_DIVIDEND),
    )
    events = {
        CorporateEvent(symbol=symbol, event_type=event_type, event_date=event_date)
        for field, event_type in fields
        for event_date in _event_dates(raw_calendar.get(field))
        if event_date >= today
    }
    return tuple(sorted(events, key=lambda event: (event.event_date, event.event_type.value)))


def _default_ticker_factory(symbol: str) -> Any:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError(
            "Falta yfinance. Ejecuta update.bat antes de consultar noticias."
        ) from exc
    return yf.Ticker(symbol)


class YahooNewsEventsProvider:
    def __init__(
        self,
        ticker_factory: Callable[[str], Any] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._ticker_factory = ticker_factory or _default_ticker_factory
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch(self, symbol: str, max_items: int = 10) -> NewsEventsResult:
        normalised_symbol = symbol.strip().upper()
        if not normalised_symbol:
            raise ValueError("El símbolo de noticias no puede estar vacío.")
        if not 1 <= max_items <= 50:
            raise ValueError("max_items debe estar entre 1 y 50.")

        captured_at = self._clock()
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=UTC)
        else:
            captured_at = captured_at.astimezone(UTC)

        errors: dict[str, str] = {}
        news: tuple[NewsItem, ...] = ()
        events: tuple[CorporateEvent, ...] = ()
        try:
            ticker = self._ticker_factory(normalised_symbol)
        except Exception as exc:
            LOGGER.exception(
                "No se pudo crear el cliente Yahoo para %s",
                normalised_symbol,
                exc_info=exc,
            )
            return NewsEventsResult(
                symbol=normalised_symbol,
                errors={"news": _NEWS_ERROR, "events": _EVENTS_ERROR},
                captured_at=captured_at,
            )

        try:
            news = normalise_news(
                ticker.get_news(count=max_items, tab="news"),
                normalised_symbol,
                max_items,
            )
        except Exception as exc:
            LOGGER.exception(
                "Falló la consulta de noticias para %s",
                normalised_symbol,
                exc_info=exc,
            )
            errors["news"] = _NEWS_ERROR

        try:
            events = normalise_calendar(
                ticker.get_calendar(),
                normalised_symbol,
                today=captured_at.date(),
            )
        except Exception as exc:
            LOGGER.exception(
                "Falló la consulta de calendario para %s",
                normalised_symbol,
                exc_info=exc,
            )
            errors["events"] = _EVENTS_ERROR

        return NewsEventsResult(
            symbol=normalised_symbol,
            news=news,
            events=events,
            errors=errors,
            captured_at=captured_at,
        )
