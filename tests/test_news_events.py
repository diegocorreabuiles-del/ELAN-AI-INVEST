from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from elan_ai_invest.news import CorporateEventType, YahooNewsEventsProvider
from elan_ai_invest.news.provider import normalise_calendar, normalise_news

NOW = datetime(2026, 7, 29, 12, tzinfo=UTC)


class FakeTicker:
    def __init__(
        self,
        news: object = (),
        calendar: object = None,
        *,
        news_error: Exception | None = None,
        calendar_error: Exception | None = None,
    ) -> None:
        self.news = news
        self.calendar = {} if calendar is None else calendar
        self.news_error = news_error
        self.calendar_error = calendar_error
        self.news_calls: list[tuple[int, str]] = []

    def get_news(self, count: int, tab: str) -> object:
        self.news_calls.append((count, tab))
        if self.news_error is not None:
            raise self.news_error
        return self.news

    def get_calendar(self) -> object:
        if self.calendar_error is not None:
            raise self.calendar_error
        return self.calendar


def test_normalise_news_supports_current_payload_and_deduplicates() -> None:
    payload = [
        {
            "content": {
                "title": "Resultado trimestral",
                "summary": "Ingresos por encima de lo esperado.",
                "provider": {"displayName": "Agencia Uno"},
                "pubDate": "2026-07-29T11:00:00Z",
                "canonicalUrl": {"url": "https://example.com/resultados"},
            }
        },
        {
            "content": {
                "title": "Resultado trimestral",
                "provider": {"displayName": "Agencia duplicada"},
                "pubDate": "2026-07-29T10:30:00Z",
                "canonicalUrl": {"url": "https://duplicate.example/resultados"},
            }
        },
        {
            "content": {
                "title": "Nueva fábrica",
                "provider": {"displayName": "Agencia Dos"},
                "pubDate": "2026-07-29T11:30:00+00:00",
                "clickThroughUrl": {"url": "https://example.com/fabrica"},
            }
        },
    ]

    result = normalise_news(payload, "AAPL", max_items=10)

    assert [item.title for item in result] == ["Nueva fábrica", "Resultado trimestral"]
    assert result[1].publisher == "Agencia Uno"
    assert result[1].summary == "Ingresos por encima de lo esperado."
    assert all(item.published_at.tzinfo is UTC for item in result)


def test_normalise_news_supports_legacy_payload_and_limit() -> None:
    payload = [
        {
            "title": f"Titular {index}",
            "publisher": "Fuente",
            "providerPublishTime": 1_775_000_000 + index,
            "link": f"https://example.com/{index}",
        }
        for index in range(4)
    ]

    result = normalise_news(payload, "MSFT", max_items=2)

    assert len(result) == 2
    assert result[0].title == "Titular 3"
    assert result[0].symbol == "MSFT"


def test_normalise_news_rejects_malformed_or_unsafe_entries() -> None:
    payload = [
        {"title": "Sin fecha", "link": "https://example.com/no-date"},
        {
            "title": "URL insegura",
            "providerPublishTime": 1_775_000_000,
            "link": "javascript:alert(1)",
        },
        "no es un artículo",
    ]

    assert normalise_news(payload, "AAPL", max_items=10) == ()
    assert normalise_news({"unexpected": "mapping"}, "AAPL", max_items=10) == ()


def test_normalise_calendar_keeps_future_supported_events() -> None:
    result = normalise_calendar(
        {
            "Earnings Date": [
                date(2026, 7, 28),
                date(2026, 8, 1),
                date(2026, 8, 1),
            ],
            "Dividend Date": date(2026, 8, 15),
            "Ex-Dividend Date": "2026-08-10",
            "Unexpected": date(2026, 9, 1),
        },
        "AAPL",
        today=date(2026, 7, 29),
    )

    assert [(event.event_type, event.event_date) for event in result] == [
        (CorporateEventType.EARNINGS, date(2026, 8, 1)),
        (CorporateEventType.EX_DIVIDEND, date(2026, 8, 10)),
        (CorporateEventType.DIVIDEND, date(2026, 8, 15)),
    ]


def test_provider_isolates_news_failure_from_calendar() -> None:
    ticker = FakeTicker(
        calendar={"Earnings Date": date(2026, 8, 1)},
        news_error=RuntimeError("detalle interno"),
    )
    provider = YahooNewsEventsProvider(lambda symbol: ticker, clock=lambda: NOW)

    result = provider.fetch(" aapl ", max_items=7)

    assert result.symbol == "AAPL"
    assert result.news == ()
    assert len(result.events) == 1
    assert result.errors == {"news": "Noticias temporalmente no disponibles."}
    assert ticker.news_calls == [(7, "news")]
    assert "detalle interno" not in result.errors["news"]


def test_provider_isolates_calendar_failure_from_news() -> None:
    ticker = FakeTicker(
        news=[
            {
                "title": "Titular válido",
                "publisher": "Fuente",
                "providerPublishTime": 1_775_000_000,
                "link": "https://example.com/valido",
            }
        ],
        calendar_error=RuntimeError("detalle interno"),
    )
    provider = YahooNewsEventsProvider(lambda symbol: ticker, clock=lambda: NOW)

    result = provider.fetch("MSFT")

    assert len(result.news) == 1
    assert result.events == ()
    assert result.errors == {"events": "Calendario corporativo temporalmente no disponible."}


def test_provider_contains_ticker_construction_failure() -> None:
    def fail_factory(symbol: str) -> object:
        raise RuntimeError(f"no disponible {symbol}")

    result = YahooNewsEventsProvider(fail_factory, clock=lambda: NOW).fetch("NVDA")

    assert result.news == ()
    assert result.events == ()
    assert set(result.errors) == {"news", "events"}
    assert all("NVDA" not in message for message in result.errors.values())


@pytest.mark.parametrize(("symbol", "max_items"), [("", 10), ("AAPL", 0), ("AAPL", 51)])
def test_provider_validates_request(symbol: str, max_items: int) -> None:
    provider = YahooNewsEventsProvider(lambda value: FakeTicker(), clock=lambda: NOW)

    with pytest.raises(ValueError):
        provider.fetch(symbol, max_items=max_items)
