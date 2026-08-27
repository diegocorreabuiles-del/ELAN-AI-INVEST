from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from elan_ai_invest.core.config import MarketConfig
from elan_ai_invest.fx import (
    HistoricalFxService,
    YahooFxHistoryProvider,
    is_fx_asset_id,
    load_currency_registry,
    normalize_fx_pair,
)
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
ANALYSIS_PERIOD_KEY = "analysis_period"
MARKET_PERIOD_REQUEST_KEY = "market_period_request"
CHART_VIEWS = ("Velas", "Línea", "Rentabilidad", "Volumen")
PRICE_SCALES = ("Lineal", "Logarítmica")
LONG_HORIZON_RESAMPLING = {
    "10y": ("W-FRI", "semanal"),
    "max": ("ME", "mensual"),
}
MAX_COMPARISON_INSTRUMENTS = 8
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
    "fx:direct": "FX directa",
    "fx:inverse": "FX inversa",
    "fx:synthetic": "FX sintética",
}


@dataclass(frozen=True)
class ComparisonData:
    normalized: pd.DataFrame
    returns: pd.DataFrame
    rolling_correlation: pd.Series
    correlation: float


@dataclass(frozen=True)
class MultiComparisonData:
    normalized: pd.DataFrame
    returns: pd.DataFrame
    correlation: pd.DataFrame


@st.cache_data(ttl=900, max_entries=50, show_spinner=False)
def _load_history(
    symbol: str,
    period: str,
    timeout_seconds: float,
    max_retries: int,
    backoff_seconds: float,
) -> pd.DataFrame:
    if is_fx_asset_id(symbol):
        root = Path(__file__).resolve().parents[3]
        service = HistoricalFxService(
            load_currency_registry(root / "config" / "currencies.csv"),
            YahooFxHistoryProvider(
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                backoff_seconds=backoff_seconds,
            ),
        )
        return service.get_history(normalize_fx_pair(symbol), period=period, interval="1d").prices
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


def _request_market_period() -> None:
    horizon_label = st.session_state.get("market_detail_horizon")
    if not isinstance(horizon_label, str):
        return
    requested_period = HORIZONS.get(horizon_label)
    if requested_period is None:
        return
    st.session_state[MARKET_PERIOD_REQUEST_KEY] = requested_period
    st.rerun(scope="app")


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


def build_multi_comparison_data(
    prices: pd.DataFrame,
    symbols: list[str],
) -> MultiComparisonData:
    selected = list(dict.fromkeys(symbols))
    if len(selected) < 2:
        raise ValueError("Selecciona al menos dos instrumentos distintos.")
    if any(symbol not in prices for symbol in selected):
        raise ValueError("Uno de los instrumentos no tiene datos en el análisis actual.")

    aligned = prices[selected].apply(pd.to_numeric, errors="coerce")
    aligned = aligned.replace([np.inf, -np.inf], np.nan).dropna()
    if len(aligned) < 3:
        raise ValueError("No hay suficientes sesiones comunes para comparar.")

    normalized = aligned.div(aligned.iloc[0]).mul(100.0)
    returns = aligned.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).dropna()
    if len(returns) < 2:
        raise ValueError("No hay suficientes rendimientos consecutivos para correlacionar.")
    return MultiComparisonData(normalized, returns, returns.corr())


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


def _resample_history_for_chart(history: pd.DataFrame, period: str | None) -> pd.DataFrame:
    resampling = LONG_HORIZON_RESAMPLING.get(period or "")
    if resampling is None:
        return history

    rule, _ = resampling
    displayed = history.resample(rule).agg(
        {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }
    )
    displayed = displayed.dropna(subset=["Open", "High", "Low", "Close"])
    observed_dates = history.index.to_series().resample(rule).max().reindex(displayed.index)
    displayed.index = pd.DatetimeIndex(observed_dates.array)
    return displayed


def _display_close(history: pd.DataFrame, displayed: pd.DataFrame) -> pd.Series:
    close = displayed["Close"].copy()
    source_close = history["Close"].dropna()
    close.loc[source_close.index[0]] = source_close.iloc[0]
    close.loc[source_close.index[-1]] = source_close.iloc[-1]
    return close.sort_index()


def _history_chart(
    history: pd.DataFrame,
    symbol: str,
    view: str,
    *,
    period: str | None = None,
    price_scale: str = "Lineal",
) -> go.Figure:
    displayed = _resample_history_for_chart(history, period)
    if view == "Velas":
        figure = go.Figure(
            go.Candlestick(
                x=displayed.index,
                open=displayed["Open"],
                high=displayed["High"],
                low=displayed["Low"],
                close=displayed["Close"],
                increasing_line_color="#21C994",
                decreasing_line_color="#FF5C70",
                name=symbol,
            )
        )
        figure.update_layout(xaxis_rangeslider_visible=False)
    elif view == "Línea":
        close = _display_close(history, displayed)
        figure = go.Figure(
            go.Scatter(
                x=close.index,
                y=close,
                mode="lines",
                line={"color": "#21C994", "width": 2},
                name="Cierre",
            )
        )
    elif view == "Rentabilidad":
        close = _display_close(history, displayed)
        baseline = float(history["Close"].dropna().iloc[0])
        performance = close.div(baseline).sub(1.0).mul(100.0)
        figure = go.Figure(
            go.Scatter(
                x=performance.index,
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
        colors = np.where(displayed["Close"].ge(displayed["Open"]), "#21C994", "#FF5C70")
        figure = go.Figure(
            go.Bar(
                x=displayed.index,
                y=displayed["Volume"],
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
    if view in {"Velas", "Línea"}:
        figure.update_yaxes(type="log" if price_scale == "Logarítmica" else "linear")
    return figure


def _correlation_label(value: float) -> str:
    if not np.isfinite(value):
        return "No disponible"
    strength = "fuerte" if abs(value) >= 0.7 else "moderada" if abs(value) >= 0.4 else "débil"
    direction = "positiva" if value > 0 else "negativa" if value < 0 else "neutra"
    return f"{strength} {direction}"


def _comparison_figures(
    comparison: ComparisonData,
    first_symbol: str,
    second_symbol: str,
    window: int,
) -> tuple[go.Figure, go.Figure, go.Figure]:
    normalized_chart = go.Figure()
    for symbol in (first_symbol, second_symbol):
        normalized_chart.add_trace(
            go.Scatter(
                x=comparison.normalized.index,
                y=comparison.normalized[symbol],
                mode="lines",
                name=symbol,
            )
        )
    normalized_chart.add_hline(y=100, line_dash="dash", line_color="#8B98A5")
    normalized_chart.update_layout(
        title="Desempeño comparable · Base 100",
        xaxis_title="Fecha",
        yaxis_title="Base 100",
        legend_title_text="Instrumento",
        height=410,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
    )

    scatter = go.Figure(
        go.Scatter(
            x=comparison.returns[first_symbol],
            y=comparison.returns[second_symbol],
            mode="markers",
            showlegend=False,
        )
    )
    scatter.update_layout(
        title="Dispersión de rendimientos diarios",
        xaxis_title=f"{first_symbol} · retorno",
        yaxis_title=f"{second_symbol} · retorno",
        height=410,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
    )
    scatter.update_xaxes(tickformat=".2%")
    scatter.update_yaxes(tickformat=".2%")

    rolling_chart = go.Figure(
        go.Scatter(
            x=comparison.rolling_correlation.index,
            y=comparison.rolling_correlation,
            mode="lines",
            name="Correlación",
        )
    )
    rolling_chart.add_hline(y=0, line_dash="dash", line_color="#8B98A5")
    rolling_chart.update_layout(
        title=f"Correlación móvil · {window} sesiones",
        xaxis_title="Fecha",
        yaxis_title="Correlación",
        height=330,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        showlegend=False,
    )
    rolling_chart.update_yaxes(range=[-1, 1])
    return normalized_chart, scatter, rolling_chart


def _multi_comparison_figures(
    comparison: MultiComparisonData,
) -> tuple[go.Figure, go.Figure]:
    normalized_chart = go.Figure()
    for symbol in comparison.normalized.columns:
        normalized_chart.add_trace(
            go.Scatter(
                x=comparison.normalized.index,
                y=comparison.normalized[symbol],
                mode="lines",
                name=symbol,
            )
        )
    normalized_chart.add_hline(y=100, line_dash="dash", line_color="#8B98A5")
    normalized_chart.update_layout(
        title="Desempeño conjunto · Base 100",
        xaxis_title="Fecha",
        yaxis_title="Base 100",
        legend_title_text="Instrumento",
        height=430,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
    )

    correlation = comparison.correlation
    matrix = go.Figure(
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
    matrix.update_layout(
        title="Matriz de correlaciones",
        height=430,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
    )
    return normalized_chart, matrix


def build_reference_correlation_data(
    returns: pd.DataFrame,
    reference_symbol: str,
    symbols: list[str],
    *,
    window: int,
) -> tuple[pd.Series, pd.DataFrame]:
    selected = list(dict.fromkeys(symbols))
    if reference_symbol not in selected:
        raise ValueError("El activo de referencia debe estar entre los instrumentos focales.")
    targets = [symbol for symbol in selected if symbol != reference_symbol]
    if not targets:
        raise ValueError("Selecciona al menos un comparable para el activo de referencia.")
    if window < 2:
        raise ValueError("La ventana de correlación debe ser de al menos 2 sesiones.")

    correlations = pd.Series(
        {symbol: float(returns[reference_symbol].corr(returns[symbol])) for symbol in targets},
        name="Correlación",
        dtype=float,
    )
    minimum_periods = min(20, window)
    rolling = pd.DataFrame(
        {
            f"{reference_symbol} / {symbol}": returns[reference_symbol]
            .rolling(window, min_periods=minimum_periods)
            .corr(returns[symbol])
            for symbol in targets
        }
    )
    return correlations, rolling.dropna(how="all")


def _reference_rolling_figure(
    rolling: pd.DataFrame,
    reference_symbol: str,
    window: int,
) -> go.Figure:
    figure = go.Figure()
    for pair in rolling.columns:
        figure.add_trace(
            go.Scatter(
                x=rolling.index,
                y=rolling[pair],
                mode="lines",
                name=pair,
            )
        )
    figure.add_hline(y=0, line_dash="dash", line_color="#8B98A5")
    figure.update_layout(
        title=f"Correlación móvil frente a {reference_symbol} · {window} sesiones",
        xaxis_title="Fecha",
        yaxis_title="Correlación",
        height=380,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        legend_title_text="Par",
    )
    figure.update_yaxes(range=[-1, 1])
    return figure


def _format_observation(value: datetime | None) -> str:
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
            "Proveedor de ruta": quality.route_provider or "N/D",
            "Ruta FX": quality.route_path or "N/D",
            "Cobertura de ruta": (
                f"{quality.route_coverage_ratio:.1%}"
                if quality.route_coverage_ratio is not None
                else "N/D"
            ),
        }
        for quality in report.assets.values()
    ]


def _render_fx_provenance(
    symbol: str,
    report: MarketDataQualityReport | None,
) -> None:
    if report is None or not is_fx_asset_id(symbol):
        return
    quality = report.assets.get(symbol)
    if quality is None:
        return

    freshness = f"{quality.age_days} días" if quality.age_days is not None else "N/D"
    route_coverage = (
        f"{quality.route_coverage_ratio:.1%}" if quality.route_coverage_ratio is not None else "N/D"
    )
    with st.container(border=True):
        st.markdown("**:material/route: Trazabilidad FX**")
        with st.container(horizontal=True):
            st.metric(
                "Resolución",
                QUALITY_SOURCE_LABELS.get(quality.source, quality.source),
                border=True,
            )
            st.metric("Proveedor de ruta", quality.route_provider or "N/D", border=True)
            st.metric("Cobertura temporal", f"{quality.coverage_ratio:.1%}", border=True)
            st.metric("Frescura", freshness, border=True)
        st.caption(
            f"Cálculo: {quality.route_path or 'N/D'} · Cobertura de ruta: {route_coverage} · "
            f"Última sesión: {_format_observation(quality.last_observation)}"
        )


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
def _render_history_detail(primary_symbol: str, market_settings: MarketConfig) -> None:
    active_period = str(st.session_state.get(ANALYSIS_PERIOD_KEY, market_settings.period))
    period_to_label = {period: label for label, period in HORIZONS.items()}
    active_horizon_label = period_to_label.get(active_period, "1 año")
    stored_horizon_label = st.session_state.get("market_detail_horizon")
    if stored_horizon_label not in HORIZONS or HORIZONS[stored_horizon_label] != active_period:
        st.session_state["market_detail_horizon"] = active_horizon_label

    with st.container(horizontal=True, vertical_alignment="bottom"):
        horizon_label = st.selectbox(
            "Horizonte del gráfico",
            list(HORIZONS),
            key="market_detail_horizon",
            on_change=_request_market_period,
        )
        chart_view = st.segmented_control(
            "Vista",
            CHART_VIEWS,
            default="Velas",
            key="market_chart_view",
        )

    selected_period = HORIZONS[horizon_label]
    price_scale = "Lineal"
    if selected_period in LONG_HORIZON_RESAMPLING and chart_view in {"Velas", "Línea"}:
        price_scale = (
            st.segmented_control(
                "Escala de precio",
                PRICE_SCALES,
                default="Logarítmica",
                key=f"market_price_scale_{selected_period}",
            )
            or "Logarítmica"
        )

    try:
        with st.spinner(f"Cargando histórico de {primary_symbol}...", show_time=True):
            history = _load_history(
                primary_symbol,
                selected_period,
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
        provider="FX routing" if is_fx_asset_id(primary_symbol) else "Yahoo",
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
            _history_chart(
                history,
                primary_symbol,
                chart_view or "Velas",
                period=selected_period,
                price_scale=price_scale,
            ),
            width="stretch",
        )
    display_frequency = LONG_HORIZON_RESAMPLING.get(selected_period)
    if display_frequency is not None:
        st.caption(
            f"Visualización {display_frequency[1]} para mejorar la legibilidad; "
            "métricas calculadas con todas las sesiones diarias."
        )
    st.caption(
        "OHLCV ajustado de Yahoo · Los máximos y mínimos corresponden al horizonte seleccionado."
    )


def _render_detail_panel(
    selected: Sequence[str],
    labels: Mapping[str, str],
    market_settings: MarketConfig,
    quality_report: MarketDataQualityReport | None = None,
) -> str:
    st.subheader(":material/candlestick_chart: Desempeño del activo")
    options = list(selected)
    sync_widget_to_active(st.session_state, "market_primary_symbol", options)
    primary_symbol = st.selectbox(
        "Activo del gráfico",
        options,
        format_func=lambda symbol: labels.get(symbol, symbol),
        key="market_primary_symbol",
        on_change=activate_from_widget,
        args=("market_primary_symbol", tuple(options)),
    )
    _render_fx_provenance(primary_symbol, quality_report)
    _render_history_detail(primary_symbol, market_settings)
    return primary_symbol


@st.fragment
def _render_comparator(
    prices: pd.DataFrame,
    primary_symbol: str,
    labels: Mapping[str, str],
) -> None:
    available = [symbol for symbol in prices.columns if not prices[symbol].dropna().empty]
    st.subheader(":material/compare_arrows: Comparador y correlación")
    if len(available) < 2:
        st.info("Añade al menos dos instrumentos al universo para activar el comparador.")
        return

    first_default = primary_symbol if primary_symbol in available else available[0]
    second_default = next(symbol for symbol in available if symbol != first_default)
    stored = st.session_state.get("comparison_symbols", [])
    valid_stored = [symbol for symbol in stored if symbol in available]
    if len(valid_stored) < 2:
        st.session_state["comparison_symbols"] = [first_default, second_default]
    elif valid_stored != list(stored):
        st.session_state["comparison_symbols"] = valid_stored

    selected_symbols = st.multiselect(
        "Instrumentos focales",
        available,
        max_selections=MAX_COMPARISON_INSTRUMENTS,
        format_func=lambda symbol: labels.get(symbol, symbol),
        key="comparison_symbols",
        help="Selecciona entre 2 y 8 instrumentos para desempeño, matriz y correlaciones móviles.",
    )
    if len(selected_symbols) < 2:
        st.info("Selecciona al menos dos instrumentos para comparar.")
        return

    reference_default = (
        primary_symbol if primary_symbol in selected_symbols else selected_symbols[0]
    )
    if st.session_state.get("comparison_reference_symbol") not in selected_symbols:
        st.session_state["comparison_reference_symbol"] = reference_default

    with st.container(horizontal=True, vertical_alignment="bottom"):
        reference_symbol = st.selectbox(
            "Activo de referencia",
            selected_symbols,
            format_func=lambda symbol: labels.get(symbol, symbol),
            key="comparison_reference_symbol",
        )
        window = st.selectbox(
            "Ventana móvil",
            [20, 60, 120],
            index=1,
            format_func=lambda value: f"{value} sesiones",
            key="comparison_window",
        )

    try:
        group = build_multi_comparison_data(prices, selected_symbols)
    except ValueError as exc:
        st.info(str(exc))
        return

    correlations, rolling = build_reference_correlation_data(
        group.returns,
        reference_symbol,
        selected_symbols,
        window=int(window),
    )
    finite_correlations = correlations[np.isfinite(correlations)]
    average_text = "N/D" if finite_correlations.empty else f"{finite_correlations.mean():.3f}"
    strongest_text = "N/D"
    weakest_text = "N/D"
    if not finite_correlations.empty:
        strongest = finite_correlations.abs().idxmax()
        weakest = finite_correlations.abs().idxmin()
        strongest_text = f"{strongest}: {finite_correlations[strongest]:.3f}"
        weakest_text = f"{weakest}: {finite_correlations[weakest]:.3f}"
    with st.container(horizontal=True):
        st.metric(
            "Activo de referencia", labels.get(reference_symbol, reference_symbol), border=True
        )
        st.metric("Comparables", str(len(correlations)), border=True)
        st.metric("Correlación media", average_text, border=True)
        st.metric("Relación más intensa", strongest_text, border=True)
        st.metric("Relación más débil", weakest_text, border=True)

    group_chart, matrix = _multi_comparison_figures(group)

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            group_chart,
            width="stretch",
            key="market_comparator_base100_svg_v4",
        )
    with right:
        st.plotly_chart(
            matrix,
            width="stretch",
            key="market_comparator_matrix_svg_v4",
        )

    if rolling.empty:
        st.info("Aún no hay suficientes sesiones para dibujar las correlaciones móviles.")
    else:
        st.plotly_chart(
            _reference_rolling_figure(rolling, reference_symbol, int(window)),
            width="stretch",
            key="market_comparator_reference_rolling_svg_v1",
        )
    st.caption(
        "La matriz compara todos los instrumentos focales y la gráfica móvil contrasta el "
        "activo de referencia con cada comparable. Se usan sesiones comunes y rendimientos "
        "diarios consecutivos, sin rellenar datos. No implica causalidad."
    )


def render_market_tab(
    ranking: pd.DataFrame,
    prices: pd.DataFrame,
    selected: Sequence[str],
    labels: Mapping[str, str],
    market_settings: MarketConfig,
    quality_report: MarketDataQualityReport | None = None,
) -> None:
    _render_quality_summary(quality_report)
    if quality_report is not None:
        st.divider()
    primary_symbol = _render_detail_panel(selected, labels, market_settings, quality_report)
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
