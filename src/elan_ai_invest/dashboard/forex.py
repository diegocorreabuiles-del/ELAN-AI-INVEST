from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from elan_ai_invest.core.config import MarketConfig
from elan_ai_invest.forex import (
    CURRENCY_SPECS,
    DEFAULT_CURRENCIES,
    ForexAnalysis,
    build_forex_analysis,
    normalize_fx_prices,
)
from elan_ai_invest.market_data import download_adjusted_close

LOGGER = logging.getLogger(__name__)
HORIZONS = {
    "6 meses": "6mo",
    "1 año": "1y",
    "2 años": "2y",
    "5 años": "5y",
}
WINDOWS = (20, 60, 120)
MAX_SELECTED_CURRENCIES = 12


def _currency_label(code: str) -> str:
    spec = CURRENCY_SPECS[code]
    return f"{code}/USD · {spec.name}"


@st.cache_data(ttl=900, max_entries=20, show_spinner=False)
def _load_forex_prices(
    currencies: tuple[str, ...],
    period: str,
    timeout_seconds: float,
    max_retries: int,
    backoff_seconds: float,
) -> tuple[pd.DataFrame, tuple[str, ...]]:
    symbols = [CURRENCY_SPECS[code].yahoo_symbol for code in currencies]
    result = download_adjusted_close(
        symbols,
        period=period,
        interval="1d",
        minimum_history=60,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
    )
    unavailable = tuple(
        code for code in currencies if CURRENCY_SPECS[code].yahoo_symbol in result.errors
    )
    if unavailable:
        LOGGER.warning("Descarga FX parcial | unavailable=%s", ",".join(unavailable))
    return normalize_fx_prices(result.prices, currencies), unavailable


def _correlation_label(value: float) -> str:
    if not np.isfinite(value):
        return "No disponible"
    strength = "fuerte" if abs(value) >= 0.7 else "moderada" if abs(value) >= 0.4 else "débil"
    direction = "positiva" if value > 0 else "negativa" if value < 0 else "neutra"
    return f"{strength} {direction}"


def _format_fx_price(value: float) -> str:
    decimals = 6 if abs(value) < 0.01 else 4 if abs(value) < 10 else 2
    return f"{value:,.{decimals}f} USD"


def _performance_figure(analysis: ForexAnalysis) -> go.Figure:
    figure = go.Figure()
    for currency in analysis.normalized.columns:
        figure.add_trace(
            go.Scatter(
                x=analysis.normalized.index,
                y=analysis.normalized[currency],
                mode="lines",
                name=currency,
            )
        )
    figure.add_hline(y=100, line_dash="dash", line_color="#8B98A5")
    figure.update_layout(
        title="Desempeño comparable · Base 100",
        xaxis_title="Fecha",
        yaxis_title="Base 100",
        legend_title_text="Divisa",
        height=430,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        hovermode="x unified",
    )
    return figure


def _correlation_figure(analysis: ForexAnalysis) -> go.Figure:
    correlation = analysis.correlation
    figure = go.Figure(
        go.Heatmap(
            z=correlation.to_numpy(),
            x=correlation.columns,
            y=correlation.index,
            zmin=-1,
            zmax=1,
            zmid=0,
            colorscale=[[0, "#FF5C70"], [0.5, "#2A333D"], [1, "#21C994"]],
            text=correlation.round(2).to_numpy(),
            texttemplate="%{text:.2f}",
            colorbar={"title": "Correlación"},
            hovertemplate="%{y} / %{x}<br>Correlación %{z:.3f}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Matriz de correlaciones",
        height=430,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
    )
    return figure


def _rolling_figure(
    analysis: ForexAnalysis,
    first_currency: str,
    second_currency: str,
    window: int,
) -> go.Figure:
    figure = go.Figure(
        go.Scatter(
            x=analysis.rolling_correlation.index,
            y=analysis.rolling_correlation,
            mode="lines",
            name="Correlación",
        )
    )
    figure.add_hline(y=0, line_dash="dash", line_color="#8B98A5")
    figure.update_layout(
        title=f"Correlación móvil {first_currency}/{second_currency} · {window} sesiones",
        xaxis_title="Fecha",
        yaxis_title="Correlación",
        height=430,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        showlegend=False,
    )
    figure.update_yaxes(range=[-1, 1])
    return figure


def _summary_table(analysis: ForexAnalysis) -> pd.DataFrame:
    summary = analysis.summary.copy()
    summary["Divisa"] = summary["currency"].map(_currency_label)
    return summary.rename(
        columns={
            "latest_usd": "USD por unidad",
            "period_return_pct": "Rentabilidad periodo",
            "volatility_pct": "Volatilidad anual",
            "observations": "Sesiones alineadas",
        }
    )[
        [
            "Divisa",
            "USD por unidad",
            "Rentabilidad periodo",
            "Volatilidad anual",
            "Sesiones alineadas",
        ]
    ]


@st.fragment
def _render_forex_dashboard(market_settings: MarketConfig) -> None:
    with st.container(horizontal=True, vertical_alignment="bottom"):
        selected = st.multiselect(
            "Divisas frente al USD",
            list(CURRENCY_SPECS),
            default=list(DEFAULT_CURRENCIES),
            max_selections=MAX_SELECTED_CURRENCIES,
            format_func=_currency_label,
            key="forex_currencies",
            help="Selecciona entre 2 y 12 divisas para comparar.",
        )
        horizon_label = st.selectbox(
            "Horizonte",
            list(HORIZONS),
            index=2,
            key="forex_horizon",
        )
        window = st.selectbox(
            "Ventana móvil",
            WINDOWS,
            index=1,
            format_func=lambda value: f"{value} sesiones",
            key="forex_window",
        )

    if len(selected) < 2:
        st.info("Selecciona al menos dos divisas para calcular correlaciones.")
        return

    try:
        with st.spinner("Cargando mercado de divisas...", show_time=True):
            prices_usd, unavailable = _load_forex_prices(
                tuple(selected),
                HORIZONS[horizon_label],
                float(market_settings.timeout_seconds),
                int(market_settings.max_retries),
                float(market_settings.backoff_seconds),
            )
    except Exception:
        LOGGER.exception("No se pudo cargar el módulo de divisas")
        st.warning("No se pudieron cargar las divisas. Prueba otro horizonte más tarde.")
        return

    if unavailable:
        st.warning("Sin histórico utilizable para: " + ", ".join(unavailable) + ".")
    available = [code for code in selected if code in prices_usd]
    if len(available) < 2:
        st.info("Se necesitan al menos dos divisas con histórico disponible.")
        return

    if st.session_state.get("forex_focus_first") not in available:
        st.session_state["forex_focus_first"] = available[0]
    if st.session_state.get("forex_focus_second") not in available or (
        st.session_state.get("forex_focus_second") == st.session_state["forex_focus_first"]
    ):
        st.session_state["forex_focus_second"] = available[1]

    with st.container(horizontal=True, vertical_alignment="bottom"):
        first_currency = st.selectbox(
            "Divisa focal A",
            available,
            format_func=_currency_label,
            key="forex_focus_first",
        )
        second_currency = st.selectbox(
            "Divisa focal B",
            available,
            format_func=_currency_label,
            key="forex_focus_second",
        )

    try:
        analysis = build_forex_analysis(
            prices_usd,
            first_currency,
            second_currency,
            window=int(window),
        )
    except ValueError as exc:
        st.info(str(exc))
        return

    focal_correlation = float(analysis.correlation.loc[first_currency, second_currency])
    correlation_text = f"{focal_correlation:.3f}" if np.isfinite(focal_correlation) else "N/D"
    latest = analysis.prices_usd.iloc[-1]
    with st.container(horizontal=True):
        st.metric(
            "Correlación focal",
            correlation_text,
            _correlation_label(focal_correlation),
            border=True,
        )
        st.metric("Sesiones alineadas", str(len(analysis.prices_usd)), border=True)
        st.metric(
            f"1 {first_currency} en USD",
            _format_fx_price(float(latest[first_currency])),
            border=True,
        )
        st.metric(
            f"1 {second_currency} en USD",
            _format_fx_price(float(latest[second_currency])),
            border=True,
        )

    st.plotly_chart(
        _performance_figure(analysis),
        width="stretch",
        key="forex_performance_svg_v1",
    )
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            _correlation_figure(analysis),
            width="stretch",
            key="forex_matrix_svg_v1",
        )
    with right:
        if analysis.rolling_correlation.empty:
            st.info("Aún no hay suficientes sesiones para la correlación móvil.")
        else:
            st.plotly_chart(
                _rolling_figure(analysis, first_currency, second_currency, int(window)),
                width="stretch",
                key="forex_rolling_svg_v1",
            )

    st.dataframe(
        _summary_table(analysis),
        hide_index=True,
        width="stretch",
        column_config={
            "USD por unidad": st.column_config.NumberColumn(format="%.6f"),
            "Rentabilidad periodo": st.column_config.NumberColumn(format="%.2f%%"),
            "Volatilidad anual": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )
    inverted = [code for code in available if CURRENCY_SPECS[code].invert]
    inversion_note = (
        " Se invierten las cotizaciones USD/XXX de " + ", ".join(inverted) + "." if inverted else ""
    )
    st.caption(
        "Todas las series expresan USD por una unidad de divisa."
        + inversion_note
        + " Correlaciones sobre rendimientos diarios consecutivos y sesiones comunes; "
        "sin forward-fill ni retornos cero inventados. La correlación no implica causalidad."
    )


def render_forex_tab(market_settings: MarketConfig) -> None:
    st.subheader(":material/currency_exchange: Divisas y correlaciones")
    st.caption("Compara la fortaleza relativa de varias monedas frente al dólar estadounidense.")
    _render_forex_dashboard(market_settings)
