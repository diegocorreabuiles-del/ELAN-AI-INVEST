from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from elan_ai_invest.market.quality import assess_market_data_quality
from elan_ai_invest.market_data import download_market_history
from elan_ai_invest.providers.base import (
    MarketDataQualityReport,
    MarketDataQualityStatus,
)

from .workspace import activate_from_widget, sync_widget_to_active

LOGGER = logging.getLogger(__name__)
HORIZONS = {
    "1 mes": "1mo",
    "3 meses": "3mo",
    "6 meses": "6mo",
    "1 año": "1y",
    "2 años": "2y",
    "5 años": "5y",
    "10 años": "10y",
    "Máximo": "max",
}
CHART_VIEWS = ("Velas", "Línea", "Rentabilidad", "Volumen")
QUALITY_STATUS_LABELS = {
    MarketDataQualityStatus.HEALTHY: "Saludable",
    MarketDataQualityStatus.DEGRADED: "Degradado",
    MarketDataQualityStatus.STALE: "Obsoleto",
    MarketDataQualityStatus.INSUFFICIENT: "Insuficiente",
    MarketDataQualityStatus.UNAVAILABLE: "No disponible",
}
QUALITY_SOURCE_LABELS = {
    "provider": "Proveedor",
    "cache": "Caché local",
    "unavailable": "No disponible",
}


@dataclass(frozen=True)
class ComparisonData:
    normalized: pd.DataFrame
    returns: pd.DataFrame
    rolling_correlation: pd.Series
    correlation: float


@st.cache_data(ttl=900, max_entries=50, show_spinner=False)
def _load_history(
    symbol: str,
    period: str,
    timeout_seconds: float,
    max_retries: int,
    backoff_seconds: float,
) -> pd.DataFrame:
    return download_market_history(
        symbol,
        period=period,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
    )


def clear_market_history_cache() -> None:
    clear = getattr(_load_history, "clear", None)
    if callable(clear):
        clear()


def build_comparison_data(
    prices: pd.DataFrame,
    first_symbol: str,
    second_symbol: str,
    *,
    window: int = 60,
) -> ComparisonData:
    if first_symbol == second_symbol:
        raise ValueError("Selecciona dos instrumentos distintos.")
    if first_symbol not in prices or second_symbol not in prices:
        raise ValueError("Uno de los instrumentos no tiene datos en el análisis actual.")
    if window < 2:
        raise ValueError("La ventana de correlación debe ser de al menos 2 sesiones.")

    aligned = prices[[first_symbol, second_symbol]].apply(pd.to_numeric, errors="coerce")
    aligned = aligned.replace([np.inf, -np.inf], np.nan).dropna()
    if len(aligned) < 3:
        raise ValueError("No hay suficientes sesiones alineadas para comparar.")

    normalized = aligned.div(aligned.iloc[0]).mul(100.0)
    returns = aligned.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).dropna()
    if len(returns) < 2:
        raise ValueError("No hay suficientes rendimientos consecutivos para correlacionar.")

    correlation = float(returns[first_symbol].corr(returns[second_symbol]))
    minimum_periods = min(20, window)
    rolling = (
        returns[first_symbol]
        .rolling(window, min_periods=minimum_periods)
        .corr(returns[second_symbol])
    )
    rolling.name = "Correlación"
    return ComparisonData(normalized, returns, rolling.dropna(), correlation)


def _price_metrics(history: pd.DataFrame) -> dict[str, float]:
    close = history["Close"].dropna()
    returns = close.pct_change(fill_method=None).dropna()
    latest = float(close.iloc[-1])
    first = float(close.iloc[0])
    maximum = float(history["High"].max())
    minimum = float(history["Low"].min())
    volatility = float(returns.std(ddof=1) * np.sqrt(252) * 100) if len(returns) > 1 else 0.0
    return {
        "latest": latest,
        "period_return_pct": (latest / first - 1.0) * 100.0,
        "maximum": maximum,
        "minimum": minimum,
        "distance_to_max_pct": (latest / maximum - 1.0) * 100.0,
        "volatility_pct": volatility,
    }


def _format_price(value: float) -> str:
    decimals = 4 if abs(value) < 10 else 2
    return f"{value:,.{decimals}f}"


def _history_chart(history: pd.DataFrame, symbol: str, view: str) -> go.Figure:
    if view == "Velas":
        figure = go.Figure(
            go.Candlestick(
                x=history.index,
                open=history["Open"],
                high=history["High"],
                low=history["Low"],
                close=history["Close"],
                increasing_line_color="#21C994",
                decreasing_line_color="#FF5C70",
                name=symbol,
            )
        )
        figure.update_layout(xaxis_rangeslider_visible=False)
    elif view == "Línea":
        figure = go.Figure(
            go.Scatter(
                x=history.index,
                y=history["Close"],
                mode="lines",
                line={"color": "#21C994", "width": 2},
                name="Cierre",
            )
        )
    elif view == "Rentabilidad":
        performance = history["Close"].div(history["Close"].iloc[0]).sub(1.0).mul(100.0)
        figure = go.Figure(
            go.Scatter(
                x=history.index,
                y=performance,
                mode="lines",
                fill="tozeroy",
                line={"color": "#4BA3FF", "width": 2},
                name="Rentabilidad",
                hovertemplate="%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>",
            )
        )
        figure.add_hline(y=0, line_dash="dash", line_color="#8B98A5")
        figure.update_yaxes(ticksuffix="%")
    else:
        colors = np.where(history["Close"].ge(history["Open"]), "#21C994", "#FF5C70")
        figure = go.Figure(
            go.Bar(
                x=history.index,
                y=history["Volume"],
                marker_color=colors,
                name="Volumen",
                hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f}<extra></extra>",
            )
        )

    figure.update_layout(
        title=f"{symbol} · {view}",
        height=520,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        hovermode="x unified" if view != "Velas" else "closest",
        legend={"orientation": "h", "y": 1.02, "x": 0},
    )
    return figure


def _correlation_label(value: float) -> str:
    if not np.isfinite(value):
        return "No disponible"
    strength = "fuerte" if abs(value) >= 0.7 else "moderada" if abs(value) >= 0.4 else "débil"
    direction = "positiva" if value > 0 else "negativa" if value < 0 else "neutra"
    return f"{strength} {direction}"


def _format_observation(value) -> str:
    return value.strftime("%d/%m/%Y") if value is not None else "N/D"


def _quality_rows(report: MarketDataQualityReport) -> list[dict[str, str | int]]:
    return [
        {
            "Instrumento": quality.symbol,
            "Estado": QUALITY_STATUS_LABELS[quality.status],
            "Origen": QUALITY_SOURCE_LABELS.get(quality.source, quality.source),
            "Observaciones": quality.observations,
            "Cobertura": f"{quality.coverage_ratio:.1%}",
            "Huecos": quality.missing_sessions,
            "Última sesión": _format_observation(quality.last_observation),
            "Antigüedad": (f"{quality.age_days} días" if quality.age_days is not None else "N/D"),
        }
        for quality in report.assets.values()
    ]


def _render_quality_summary(report: MarketDataQualityReport | None) -> None:
    if report is None:
        return

    st.subheader(":material/monitoring: Calidad de datos")
    with st.container(horizontal=True):
        st.metric("Proveedor", report.provider, border=True)
        st.metric(
            "Calidad global",
            QUALITY_STATUS_LABELS[report.status],
            border=True,
        )
        st.metric(
            "Cobertura media",
            f"{report.average_coverage_ratio:.1%}",
            border=True,
        )
        st.metric(
            "Incidencias",
            f"{report.issue_count}/{len(report.assets)}",
            border=True,
        )

    if report.status is MarketDataQualityStatus.HEALTHY:
        st.success("El proveedor entregó historiales recientes y con cobertura suficiente.")
    elif report.status is MarketDataQualityStatus.UNAVAILABLE:
        st.warning("El proveedor no entregó históricos utilizables para el universo solicitado.")
    else:
        st.warning(
            f"{report.issue_count} de {len(report.assets)} instrumentos requieren atención. "
            "Revisa frescura, cobertura o disponibilidad antes de tomar decisiones."
        )

    details = st.expander("Detalle de calidad por instrumento", on_change="rerun")
    if details.open:
        with details:
            st.dataframe(pd.DataFrame(_quality_rows(report)), hide_index=True, width="stretch")


@st.fragment
def _render_history_detail(primary_symbol: str, market_settings) -> None:
    with st.container(horizontal=True, vertical_alignment="bottom"):
        horizon_label = st.selectbox(
            "Horizonte del gráfico",
            list(HORIZONS),
            index=3,
            key="market_detail_horizon",
        )
        chart_view = st.segmented_control(
            "Vista",
            CHART_VIEWS,
            default="Velas",
            key="market_chart_view",
        )

    try:
        with st.spinner(f"Cargando histórico de {primary_symbol}...", show_time=True):
            history = _load_history(
                primary_symbol,
                HORIZONS[horizon_label],
                float(market_settings.timeout_seconds),
                int(market_settings.max_retries),
                float(market_settings.backoff_seconds),
            )
    except Exception:
        LOGGER.exception("No se pudo cargar OHLCV | symbol=%s", primary_symbol)
        st.warning(
            "No se pudo cargar el histórico detallado de este símbolo. "
            "Prueba otro horizonte o instrumento."
        )
        return

    detail_quality_report = assess_market_data_quality(
        history[["Close"]].rename(columns={"Close": primary_symbol}),
        [primary_symbol],
        minimum_history=2,
        provider="Yahoo",
    )
    detail_quality = detail_quality_report.assets[primary_symbol]
    if detail_quality.status in {
        MarketDataQualityStatus.STALE,
        MarketDataQualityStatus.INSUFFICIENT,
    }:
        st.warning(
            "El histórico detallado está "
            f"{QUALITY_STATUS_LABELS[detail_quality.status].lower()}. "
            "Confirma su vigencia antes de usarlo."
        )
    elif detail_quality.status is MarketDataQualityStatus.DEGRADED:
        st.info(
            f"El histórico contiene {detail_quality.missing_sessions} posibles huecos "
            "de sesión; no se han rellenado artificialmente."
        )
    st.caption(
        f"Calidad OHLCV: {QUALITY_STATUS_LABELS[detail_quality.status]} · "
        f"Cobertura {detail_quality.coverage_ratio:.1%} · "
        f"Última sesión {_format_observation(detail_quality.last_observation)}"
    )

    metrics = _price_metrics(history)
    with st.container(horizontal=True):
        st.metric(
            "Último cierre",
            _format_price(metrics["latest"]),
            f"{metrics['period_return_pct']:+.2f}% en el periodo",
            border=True,
            chart_data=history["Close"].tail(40).tolist(),
            chart_type="line",
        )
        st.metric("Máximo", _format_price(metrics["maximum"]), border=True)
        st.metric("Mínimo", _format_price(metrics["minimum"]), border=True)
        st.metric(
            "Distancia al máximo",
            f"{metrics['distance_to_max_pct']:.2f}%",
            border=True,
        )
        st.metric("Volatilidad anual", f"{metrics['volatility_pct']:.2f}%", border=True)

    if chart_view == "Volumen" and not history["Volume"].gt(0).any():
        st.info("Yahoo no publica volumen para este instrumento en el horizonte seleccionado.")
    else:
        st.plotly_chart(
            _history_chart(history, primary_symbol, chart_view or "Velas"),
            width="stretch",
        )
    st.caption(
        "OHLCV ajustado de Yahoo · Los máximos y mínimos corresponden al horizonte seleccionado."
    )


def _render_detail_panel(selected, labels, market_settings) -> str:
    st.subheader(":material/candlestick_chart: Desempeño del activo")
    options = list(selected)
    sync_widget_to_active(st.session_state, "market_primary_symbol", options)
    primary_symbol = st.selectbox(
        "Activo principal",
        options,
        format_func=lambda symbol: labels.get(symbol, symbol),
        key="market_primary_symbol",
        on_change=activate_from_widget,
        args=("market_primary_symbol", tuple(options)),
    )
    _render_history_detail(primary_symbol, market_settings)
    return primary_symbol


@st.fragment
def _render_comparator(prices: pd.DataFrame, primary_symbol: str, labels) -> None:
    available = [symbol for symbol in prices.columns if not prices[symbol].dropna().empty]
    st.subheader(":material/compare_arrows: Comparador y correlación")
    if len(available) < 2:
        st.info("Añade al menos dos instrumentos al universo para activar el comparador.")
        return

    default_first = available.index(primary_symbol) if primary_symbol in available else 0
    with st.container(horizontal=True, vertical_alignment="bottom"):
        first_symbol = st.selectbox(
            "Instrumento A",
            available,
            index=default_first,
            format_func=lambda symbol: labels.get(symbol, symbol),
            key="comparison_first_symbol",
        )
        second_default = 1 if default_first == 0 else 0
        second_symbol = st.selectbox(
            "Instrumento B",
            available,
            index=second_default,
            format_func=lambda symbol: labels.get(symbol, symbol),
            key="comparison_second_symbol",
        )
        window = st.selectbox(
            "Ventana móvil",
            [20, 60, 120],
            index=1,
            format_func=lambda value: f"{value} sesiones",
            key="comparison_window",
        )

    try:
        comparison = build_comparison_data(
            prices,
            first_symbol,
            second_symbol,
            window=int(window),
        )
    except ValueError as exc:
        st.info(str(exc))
        return

    correlation_value = comparison.correlation
    correlation_text = f"{correlation_value:.3f}" if np.isfinite(correlation_value) else "N/D"
    st.metric(
        "Correlación de rendimientos diarios",
        correlation_text,
        _correlation_label(correlation_value),
        border=True,
    )

    left, right = st.columns(2)
    with left:
        normalized = (
            comparison.normalized.rename_axis("Fecha")
            .reset_index()
            .melt(id_vars="Fecha", var_name="Instrumento", value_name="Base 100")
        )
        normalized_chart = px.line(
            normalized,
            x="Fecha",
            y="Base 100",
            color="Instrumento",
            title="Desempeño comparable · Base 100",
        )
        normalized_chart.add_hline(y=100, line_dash="dash", line_color="#8B98A5")
        normalized_chart.update_layout(height=410, margin={"l": 20, "r": 20, "t": 55, "b": 20})
        st.plotly_chart(normalized_chart, width="stretch")
    with right:
        scatter = px.scatter(
            comparison.returns.reset_index(),
            x=first_symbol,
            y=second_symbol,
            title="Dispersión de rendimientos diarios",
            labels={
                first_symbol: f"{first_symbol} · retorno",
                second_symbol: f"{second_symbol} · retorno",
            },
        )
        scatter.update_layout(height=410, margin={"l": 20, "r": 20, "t": 55, "b": 20})
        scatter.update_xaxes(tickformat=".2%")
        scatter.update_yaxes(tickformat=".2%")
        st.plotly_chart(scatter, width="stretch")

    if comparison.rolling_correlation.empty:
        st.info("Aún no hay suficientes sesiones para dibujar la correlación móvil.")
    else:
        rolling = comparison.rolling_correlation.rename_axis("Fecha").reset_index()
        rolling_chart = px.line(
            rolling,
            x="Fecha",
            y="Correlación",
            title=f"Correlación móvil · {window} sesiones",
            range_y=[-1, 1],
        )
        rolling_chart.add_hline(y=0, line_dash="dash", line_color="#8B98A5")
        rolling_chart.update_layout(height=330, margin={"l": 20, "r": 20, "t": 55, "b": 20})
        st.plotly_chart(rolling_chart, width="stretch")

    st.caption(
        "La correlación usa rendimientos diarios consecutivos y alineados. "
        "No implica causalidad ni garantiza que la relación se mantenga."
    )


def render_market_tab(ranking, prices, selected, labels, market_settings, quality_report=None):
    _render_quality_summary(quality_report)
    if quality_report is not None:
        st.divider()
    primary_symbol = _render_detail_panel(selected, labels, market_settings)
    st.divider()
    _render_comparator(prices, primary_symbol, labels)
    st.divider()

    opportunities = st.expander("Mapa de oportunidades y top 5", on_change="rerun")
    if opportunities.open:
        with opportunities:
            left, right = st.columns([1.2, 0.8])
            with left:
                bubble = px.scatter(
                    ranking,
                    x="volatility_pct",
                    y="score",
                    size=ranking["return_3m_pct"].abs().clip(lower=1),
                    hover_name="name",
                    hover_data=["symbol", "signal", "confidence", "return_3m_pct"],
                    title="Mapa de oportunidades",
                )
                bubble.add_hline(y=60, line_dash="dash")
                st.plotly_chart(bubble, width="stretch")
            with right:
                st.subheader("Top 5")
                for _, row in ranking.head(5).iterrows():
                    st.markdown(
                        f"**{row['symbol']} · {row['name']}**  \nScore **{row['score']:.1f}** · 3m {row['return_3m_pct']:+.1f}% · Vol. {row['volatility_pct']:.1f}%"
                    )
                    st.progress(int(max(0, min(100, row["score"]))))
