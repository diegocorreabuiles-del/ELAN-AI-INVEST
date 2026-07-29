from __future__ import annotations

import re
from datetime import UTC, datetime

import pandas as pd
import streamlit as st

from elan_ai_invest.core.config import NewsConfig
from elan_ai_invest.news import (
    CorporateEventType,
    NewsEventsResult,
    YahooNewsEventsProvider,
)

_EVENT_LABELS = {
    CorporateEventType.EARNINGS: "Resultados",
    CorporateEventType.DIVIDEND: "Dividendo",
    CorporateEventType.EX_DIVIDEND: "Fecha ex-dividendo",
}
_MARKDOWN_CONTROL = re.compile(r"([\\`*_\[\]<>#!|])")


def _escape_markdown(value: str) -> str:
    return _MARKDOWN_CONTROL.sub(r"\\\1", value)


def _cache_bucket(ttl_seconds: int, now: datetime | None = None) -> int:
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return int(moment.timestamp() // ttl_seconds)


@st.cache_data(max_entries=50, show_spinner=False)
def _load_news_events(
    symbol: str,
    max_items: int,
    cache_bucket: int,
) -> NewsEventsResult:
    del cache_bucket
    return YahooNewsEventsProvider().fetch(symbol, max_items=max_items)


def _symbol_options(ranking: pd.DataFrame) -> tuple[list[str], dict[str, str]]:
    if "symbol" not in ranking:
        return [], {}
    symbols = list(dict.fromkeys(ranking["symbol"].dropna().astype(str).str.upper()))
    labels = {symbol: symbol for symbol in symbols}
    if "name" in ranking:
        for row in ranking[["symbol", "name"]].dropna(subset=["symbol"]).itertuples(index=False):
            symbol = str(row.symbol).upper()
            name = str(row.name).strip()
            labels[symbol] = f"{symbol} · {name}" if name and name != symbol else symbol
    return symbols, labels


def render_news_events_tab(ranking: pd.DataFrame, settings: NewsConfig) -> None:
    st.subheader("Noticias y eventos")
    st.caption(
        "Contexto informativo por activo. No modifica scores, señales, carteras ni operaciones."
    )
    if not settings.enabled:
        st.info("News & Events Engine está desactivado en config/settings.yaml.")
        return

    symbols, labels = _symbol_options(ranking)
    if not symbols:
        st.info("No hay activos disponibles para consultar noticias.")
        return

    symbol = st.selectbox(
        "Activo para noticias",
        symbols,
        format_func=lambda value: labels.get(value, value),
        key="news_events_symbol",
    )
    with st.spinner("Consultando noticias y calendario...", show_time=True):
        result = _load_news_events(
            symbol,
            settings.max_items,
            _cache_bucket(settings.cache_ttl_seconds),
        )

    metrics = st.columns(3)
    metrics[0].metric("Noticias", len(result.news), border=True)
    metrics[1].metric("Próximos eventos", len(result.events), border=True)
    metrics[2].metric("Proveedor", result.provider, border=True)
    st.caption(
        "Actualizado "
        + result.captured_at.astimezone(UTC).strftime("%d/%m/%Y %H:%M UTC")
        + f" · caché {settings.cache_ttl_seconds // 60} min"
    )

    if result.errors:
        unavailable = []
        if "news" in result.errors:
            unavailable.append("noticias")
        if "events" in result.errors:
            unavailable.append("calendario")
        st.warning("Información parcial: no se pudo actualizar " + " y ".join(unavailable) + ".")

    news_column, events_column = st.columns([0.66, 0.34], gap="large")
    with news_column:
        st.markdown("#### Noticias recientes")
        if not result.news:
            st.info("No hay noticias recientes disponibles para este activo.")
        for index, item in enumerate(result.news):
            with st.container(border=True):
                st.markdown(f"**{_escape_markdown(item.title)}**")
                st.caption(
                    _escape_markdown(item.publisher)
                    + " · "
                    + item.published_at.astimezone(UTC).strftime("%d/%m/%Y %H:%M UTC")
                )
                if item.summary:
                    st.markdown(_escape_markdown(item.summary))
                st.link_button(
                    "Abrir fuente",
                    item.url,
                    key=f"news_source_{item.symbol}_{index}",
                    icon=":material/open_in_new:",
                    width="content",
                )

    with events_column:
        st.markdown("#### Calendario")
        if not result.events:
            st.info("No hay próximos eventos corporativos disponibles.")
        for event in result.events:
            with st.container(border=True):
                st.markdown(f"**{_EVENT_LABELS[event.event_type]}**")
                st.caption(event.event_date.strftime("%d/%m/%Y"))
