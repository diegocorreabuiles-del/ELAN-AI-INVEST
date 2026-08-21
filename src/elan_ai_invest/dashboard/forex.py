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
from elan_ai_invest.fx import (
    CORRELATION_PERIODS,
    ROLLING_WINDOWS,
    FxHistory,
    FxPair,
    HistoricalFxService,
    YahooFxHistoryProvider,
    assess_fx_quality,
    build_virtual_fx_catalog,
    compute_fx_kpis,
    correlation_matrix,
    correlation_statistics,
    is_fx_asset_id,
    load_currency_registry,
    normalize_fx_pair,
    rolling_correlation,
    search_fx_pairs,
)
from elan_ai_invest.instruments import labels_by_symbol, search_instruments
from elan_ai_invest.market.cache import MarketCache
from elan_ai_invest.market_data import download_adjusted_close, download_market_history

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


FX_HORIZONS = {
    "1 mes": "1mo",
    "3 meses": "3mo",
    "6 meses": "6mo",
    "YTD": "ytd",
    "1 año": "1y",
    "3 años": "3y",
    "5 años": "5y",
    "10 años": "10y",
    "Máximo": "max",
}
MAX_FX_COMPARISON_ASSETS = 8


@st.cache_data(ttl=900, max_entries=100, show_spinner=False)
def _load_fx_pair_history(
    asset_id: str,
    period: str,
    timeout_seconds: float,
    max_retries: int,
    backoff_seconds: float,
    cache_directory: str,
    cache_ttl_seconds: int,
) -> FxHistory:
    registry = load_currency_registry()
    provider = YahooFxHistoryProvider(
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
        cache=MarketCache(cache_directory, ttl_seconds=cache_ttl_seconds),
    )
    return HistoricalFxService(registry, provider).get_history(
        normalize_fx_pair(asset_id),
        period=period,
    )


@st.cache_data(ttl=900, max_entries=100, show_spinner=False)
def _load_comparison_close(
    symbol: str,
    period: str,
    timeout_seconds: float,
    max_retries: int,
    backoff_seconds: float,
    cache_directory: str,
    cache_ttl_seconds: int,
) -> pd.Series:
    history = download_market_history(
        symbol,
        period=period,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
        cache=MarketCache(cache_directory, ttl_seconds=cache_ttl_seconds),
    )
    return history["Close"].rename(symbol)


def _normalize_comparison_series(series: pd.Series) -> pd.Series:
    result = series.copy()
    result.index = pd.to_datetime(result.index, errors="coerce", utc=True)
    result = result.loc[result.index.notna()].sort_index()
    return result.loc[~result.index.duplicated(keep="last")]


def _set_selected_fx_pair(asset_id: str) -> None:
    pair = normalize_fx_pair(asset_id)
    st.session_state["fx_engine_base"] = pair.base
    st.session_state["fx_engine_quote"] = pair.quote


def _invert_selected_fx_pair() -> None:
    base = st.session_state.get("fx_engine_base", "EUR")
    quote = st.session_state.get("fx_engine_quote", "COP")
    st.session_state["fx_engine_base"] = quote
    st.session_state["fx_engine_quote"] = base


def _add_fx_comparison_asset(asset_id: str) -> None:
    stored = list(st.session_state.get("fx_comparison_assets", []))
    if asset_id not in stored and len(stored) < MAX_FX_COMPARISON_ASSETS:
        stored.append(asset_id)
    st.session_state["fx_comparison_assets"] = stored


def _format_pair_rate(value: float) -> str:
    absolute = abs(value)
    decimals = 8 if absolute < 0.001 else 6 if absolute < 1 else 4 if absolute < 100 else 2
    return f"{value:,.{decimals}f}"


def _format_optional_pct(value: float | None) -> str:
    return "N/D" if value is None or not np.isfinite(value) else f"{value:+.2f}%"


def _fx_history_figure(history: FxHistory) -> go.Figure:
    figure = go.Figure(
        go.Scatter(
            x=history.prices.index,
            y=history.prices["Close"],
            mode="lines",
            name=history.pair.display,
        )
    )
    figure.update_layout(
        title=f"Histórico {history.pair.display}",
        xaxis_title="Fecha",
        yaxis_title=history.pair.display,
        height=430,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        hovermode="x unified",
    )
    return figure


def _comparison_base100_figure(prices: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    for symbol in prices.columns:
        series = prices[symbol].dropna()
        if series.empty:
            continue
        normalized = series.div(series.iloc[0]).mul(100.0)
        figure.add_trace(go.Scatter(x=normalized.index, y=normalized, mode="lines", name=symbol))
    figure.add_hline(y=100, line_dash="dash", line_color="#8B98A5")
    figure.update_layout(
        title="Comparación multiactivo · Base 100",
        xaxis_title="Fecha",
        yaxis_title="Base 100",
        height=430,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        hovermode="x unified",
    )
    return figure


def _fx_matrix_figure(values: pd.DataFrame) -> go.Figure:
    figure = go.Figure(
        go.Heatmap(
            z=values.to_numpy(),
            x=values.columns,
            y=values.index,
            zmin=-1,
            zmax=1,
            zmid=0,
            colorscale=[[0, "#FF5C70"], [0.5, "#2A333D"], [1, "#21C994"]],
            text=values.round(2).to_numpy(),
            texttemplate="%{text:.2f}",
            colorbar={"title": "Correlación"},
            hovertemplate="%{y} / %{x}<br>Correlación %{z:.3f}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Matriz de correlaciones sobre log returns",
        height=430,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
    )
    return figure


def _fx_rolling_chart(
    values: pd.Series,
    first: str,
    second: str,
    window: int,
) -> go.Figure:
    figure = go.Figure(go.Scatter(x=values.index, y=values, mode="lines", name="Correlación"))
    figure.add_hline(y=0, line_dash="dash", line_color="#8B98A5")
    figure.update_layout(
        title=f"Correlación móvil {first} / {second} · {window} sesiones",
        xaxis_title="Fecha",
        yaxis_title="Correlación",
        height=430,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        showlegend=False,
    )
    figure.update_yaxes(range=[-1, 1])
    return figure


def _related_fx_pairs(pair: FxPair) -> tuple[FxPair, ...]:
    candidates: list[FxPair] = []
    if pair.base != "USD":
        candidates.append(FxPair(pair.base, "USD"))
    if pair.quote != "USD":
        candidates.append(FxPair("USD", pair.quote))
    candidates.append(pair.inverse())
    unique = {candidate.asset_id: candidate for candidate in candidates}
    return tuple(unique.values())


def _render_fx_comparator(
    pair: FxPair,
    history: FxHistory,
    period: str,
    market_settings: MarketConfig,
    virtual_catalog: pd.DataFrame,
    instrument_catalog: pd.DataFrame | None,
) -> None:
    st.subheader(":material/compare_arrows: Comparador multiactivo")
    related = _related_fx_pairs(pair)
    defaults = [pair.asset_id]
    defaults.extend(item.asset_id for item in related[:2])
    stored = list(st.session_state.get("fx_comparison_assets", []))
    if not stored:
        st.session_state["fx_comparison_assets"] = list(dict.fromkeys(defaults))
        stored = list(st.session_state["fx_comparison_assets"])

    with st.container(horizontal=True, vertical_alignment="bottom"):
        fx_query = st.text_input(
            "Buscar otro par FX",
            placeholder="Ej.: COP, peso colombiano, USD/MXN",
            key="fx_comparison_search",
        )
        fx_results = search_fx_pairs(virtual_catalog, fx_query, limit=30)
        fx_options = fx_results["asset_id"].tolist()
        fx_labels = dict(zip(fx_results["asset_id"], fx_results["label"], strict=True))
        fx_choice = st.selectbox(
            "Resultado FX",
            fx_options,
            index=0 if fx_options else None,
            format_func=lambda value: fx_labels.get(value, value),
            disabled=not fx_options,
            key="fx_comparison_result",
        )
        st.button(
            "Añadir par",
            icon=":material/add:",
            disabled=fx_choice is None,
            on_click=_add_fx_comparison_asset,
            args=(fx_choice or pair.asset_id,),
            key="fx_add_pair",
        )

    regular_labels: dict[str, str] = {}
    if instrument_catalog is not None:
        with st.container(horizontal=True, vertical_alignment="bottom"):
            asset_query = st.text_input(
                "Buscar acción, índice, materia prima o cripto",
                placeholder="Ej.: Brent, BTC, S&P 500, Ecopetrol",
                key="fx_asset_search",
            )
            asset_results = search_instruments(instrument_catalog, asset_query, limit=30)
            asset_options = asset_results["symbol"].tolist()
            regular_labels = labels_by_symbol(asset_results)
            asset_choice = st.selectbox(
                "Resultado de activo",
                asset_options,
                index=0 if asset_options else None,
                format_func=lambda value: regular_labels.get(value, value),
                disabled=not asset_options,
                key="fx_asset_result",
            )
            st.button(
                "Añadir activo",
                icon=":material/add:",
                disabled=asset_choice is None,
                on_click=_add_fx_comparison_asset,
                args=(asset_choice or "SPY",),
                key="fx_add_asset",
            )

    stored = list(st.session_state.get("fx_comparison_assets", []))
    all_fx_labels = dict(zip(virtual_catalog["asset_id"], virtual_catalog["label"], strict=True))
    if instrument_catalog is not None:
        regular_labels = labels_by_symbol(instrument_catalog)

    def item_label(asset_id: str) -> str:
        return all_fx_labels.get(asset_id, regular_labels.get(asset_id, asset_id))

    selected = st.multiselect(
        "Elementos del comparador",
        stored,
        default=stored,
        max_selections=MAX_FX_COMPARISON_ASSETS,
        format_func=item_label,
        key="fx_comparison_selected",
        help="Hasta ocho pares FX o activos. Los cruces permanecen en análisis de solo lectura.",
    )
    st.session_state["fx_comparison_assets"] = list(selected)
    if len(selected) < 2:
        st.info("Añade y conserva al menos dos elementos para calcular correlaciones.")
        return

    with st.container(horizontal=True, vertical_alignment="bottom"):
        correlation_period = st.selectbox(
            "Periodo estadístico",
            list(CORRELATION_PERIODS),
            index=1,
            key="fx_correlation_period",
        )
        rolling_window = st.selectbox(
            "Ventana rolling",
            ROLLING_WINDOWS,
            index=1,
            format_func=lambda value: f"{value} sesiones",
            key="fx_engine_rolling_window",
        )

    series: dict[str, pd.Series] = {}
    unavailable: list[str] = []
    for asset_id in selected:
        try:
            if asset_id == pair.asset_id:
                series[asset_id] = history.prices["Close"].rename(asset_id)
            elif is_fx_asset_id(asset_id):
                item = _load_fx_pair_history(
                    asset_id,
                    period,
                    float(market_settings.timeout_seconds),
                    int(market_settings.max_retries),
                    float(market_settings.backoff_seconds),
                    market_settings.cache_directory,
                    int(market_settings.cache_ttl_seconds),
                )
                series[asset_id] = item.prices["Close"].rename(asset_id)
            else:
                series[asset_id] = _load_comparison_close(
                    asset_id,
                    period,
                    float(market_settings.timeout_seconds),
                    int(market_settings.max_retries),
                    float(market_settings.backoff_seconds),
                    market_settings.cache_directory,
                    int(market_settings.cache_ttl_seconds),
                )
        except Exception:
            LOGGER.exception("Elemento no disponible para comparador FX | asset=%s", asset_id)
            unavailable.append(asset_id)
    if unavailable:
        st.warning("Sin histórico utilizable para: " + ", ".join(map(item_label, unavailable)))
    if len(series) < 2:
        st.info("Se necesitan al menos dos históricos disponibles.")
        return

    prices = pd.concat(
        (_normalize_comparison_series(item) for item in series.values()),
        axis=1,
        sort=False,
    ).sort_index()
    matrix = correlation_matrix(
        prices,
        lookback_sessions=CORRELATION_PERIODS[correlation_period],
    )
    available = list(series)
    if st.session_state.get("fx_correlation_first") not in available:
        st.session_state["fx_correlation_first"] = available[0]
    if st.session_state.get("fx_correlation_second") not in available or st.session_state.get(
        "fx_correlation_second"
    ) == st.session_state.get("fx_correlation_first"):
        st.session_state["fx_correlation_second"] = available[1]
    with st.container(horizontal=True, vertical_alignment="bottom"):
        first = st.selectbox(
            "Elemento focal A",
            available,
            format_func=item_label,
            key="fx_correlation_first",
        )
        second = st.selectbox(
            "Elemento focal B",
            available,
            format_func=item_label,
            key="fx_correlation_second",
        )

    stats = correlation_statistics(
        prices[first],
        prices[second],
        lookback_sessions=CORRELATION_PERIODS[correlation_period],
    )
    rolling = rolling_correlation(prices[first], prices[second], window=int(rolling_window))
    correlation_text = "N/D" if stats.correlation is None else f"{stats.correlation:.3f}"
    dates = (
        "N/D"
        if stats.start_date is None or stats.end_date is None
        else f"{stats.start_date:%d/%m/%Y} → {stats.end_date:%d/%m/%Y}"
    )
    with st.container(horizontal=True):
        st.metric("Correlación", correlation_text, border=True)
        st.metric("Periodo", correlation_period, border=True)
        st.metric("Observaciones", str(stats.observations), border=True)
        st.metric("Cobertura", f"{stats.coverage_ratio:.1%}", border=True)
        st.metric("Fechas", dates, border=True)

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            _comparison_base100_figure(prices),
            width="stretch",
            key="fx_engine_base100_svg_v1",
        )
    with right:
        st.plotly_chart(
            _fx_matrix_figure(matrix.correlation),
            width="stretch",
            key="fx_engine_matrix_svg_v1",
        )
    if rolling.empty:
        st.info("No hay suficientes observaciones para la correlación móvil seleccionada.")
    else:
        st.plotly_chart(
            _fx_rolling_chart(rolling, first, second, int(rolling_window)),
            width="stretch",
            key="fx_engine_rolling_svg_v1",
        )

    detail = st.expander("Detalle de cobertura y observaciones", on_change="rerun")
    if detail.open:
        with detail:
            st.markdown("**Observaciones por combinación**")
            st.dataframe(matrix.observations, width="stretch")
            st.markdown("**Cobertura por combinación**")
            st.dataframe(matrix.coverage, width="stretch")
    st.caption(
        "Correlaciones sobre log returns y fechas comunes por cada combinación; "
        "sin forward-fill, interpolación ni retornos cero inventados."
    )


def _render_fx_engine_dashboard(
    market_settings: MarketConfig,
    instrument_catalog: pd.DataFrame | None,
) -> None:
    registry = load_currency_registry()
    virtual_catalog = build_virtual_fx_catalog(registry)
    codes = list(registry.codes())
    if st.session_state.get("fx_engine_base") not in codes:
        st.session_state["fx_engine_base"] = "EUR"
    if st.session_state.get("fx_engine_quote") not in codes:
        st.session_state["fx_engine_quote"] = "COP"
    if st.session_state["fx_engine_base"] == st.session_state["fx_engine_quote"]:
        st.session_state["fx_engine_quote"] = next(
            code for code in codes if code != st.session_state["fx_engine_base"]
        )

    query = st.text_input(
        "Buscar moneda o par",
        placeholder="Ej.: COP, peso colombiano, Colombia, EUR/COP",
        icon=":material/search:",
        key="fx_pair_search",
    )
    search_results = search_fx_pairs(virtual_catalog, query, limit=40)
    result_options = search_results["asset_id"].tolist()
    result_labels = dict(zip(search_results["asset_id"], search_results["label"], strict=True))
    with st.container(horizontal=True, vertical_alignment="bottom"):
        search_choice = st.selectbox(
            "Pares encontrados",
            result_options,
            index=0 if result_options else None,
            format_func=lambda value: result_labels.get(value, value),
            disabled=not result_options,
            key="fx_pair_search_result",
        )
        st.button(
            "Abrir par",
            icon=":material/open_in_new:",
            disabled=search_choice is None,
            on_click=_set_selected_fx_pair,
            args=(search_choice or "FX_EUR_COP",),
            key="fx_open_pair",
        )

    with st.container(horizontal=True, vertical_alignment="bottom"):
        base = st.selectbox(
            "Divisa base",
            codes,
            format_func=lambda code: f"{code} · {registry.get(code).name}",
            key="fx_engine_base",
        )
        quote = st.selectbox(
            "Divisa cotizada",
            codes,
            format_func=lambda code: f"{code} · {registry.get(code).name}",
            key="fx_engine_quote",
        )
        st.button(
            "Invertir",
            icon=":material/swap_horiz:",
            on_click=_invert_selected_fx_pair,
            key="fx_invert_pair",
        )
        horizon_label = st.selectbox(
            "Horizonte",
            list(FX_HORIZONS),
            index=4,
            key="fx_engine_horizon",
        )
    if base == quote:
        st.info("Selecciona divisas base y cotizada distintas.")
        return
    pair = FxPair(base, quote)

    try:
        with st.spinner(f"Resolviendo {pair.display}...", show_time=True):
            history = _load_fx_pair_history(
                pair.asset_id,
                FX_HORIZONS[horizon_label],
                float(market_settings.timeout_seconds),
                int(market_settings.max_retries),
                float(market_settings.backoff_seconds),
                market_settings.cache_directory,
                int(market_settings.cache_ttl_seconds),
            )
    except Exception:
        LOGGER.exception("No se pudo resolver el par FX | pair=%s", pair.display)
        st.warning(
            f"No hay una ruta fiable disponible para {pair.display}. Prueba otro horizonte o par."
        )
        return

    kpis = compute_fx_kpis(history.prices)
    quality = assess_fx_quality(history)
    st.subheader(pair.display)
    st.caption(
        f"1 {pair.base} = {_format_pair_rate(kpis.latest)} {pair.quote} · "
        f":blue-badge[{history.route.source_type.value}]"
    )
    with st.container(horizontal=True):
        st.metric("Precio actual", _format_pair_rate(kpis.latest), border=True)
        st.metric("Variación 1D", _format_optional_pct(kpis.change_1d_pct), border=True)
        st.metric("Variación 7D", _format_optional_pct(kpis.change_7d_pct), border=True)
        st.metric("Variación 30D", _format_optional_pct(kpis.change_30d_pct), border=True)
        st.metric("YTD", _format_optional_pct(kpis.ytd_pct), border=True)
        st.metric("1 año", _format_optional_pct(kpis.change_1y_pct), border=True)
    with st.container(horizontal=True):
        st.metric("Volatilidad 30D", _format_optional_pct(kpis.volatility_30d_pct), border=True)
        st.metric("Volatilidad 1Y", _format_optional_pct(kpis.volatility_1y_pct), border=True)
        st.metric(
            "Máximo 52W",
            "N/D" if kpis.high_52w is None else _format_pair_rate(kpis.high_52w),
            border=True,
        )
        st.metric(
            "Mínimo 52W",
            "N/D" if kpis.low_52w is None else _format_pair_rate(kpis.low_52w),
            border=True,
        )
        st.metric("RSI14", "N/D" if kpis.rsi_14 is None else f"{kpis.rsi_14:.1f}", border=True)
        st.metric("Tendencia", kpis.trend, border=True)

    with st.container(horizontal=True):
        st.metric(
            "Distancia máximo 52W", _format_optional_pct(kpis.distance_to_high_52w_pct), border=True
        )
        st.metric(
            "Distancia mínimo 52W", _format_optional_pct(kpis.distance_to_low_52w_pct), border=True
        )
        st.metric(
            "SMA50",
            "N/D" if kpis.sma_50 is None else _format_pair_rate(kpis.sma_50),
            border=True,
        )
        st.metric(
            "SMA200",
            "N/D" if kpis.sma_200 is None else _format_pair_rate(kpis.sma_200),
            border=True,
        )
        st.metric(
            "ATR14",
            "N/D" if kpis.atr_14 is None else _format_pair_rate(kpis.atr_14),
            border=True,
        )

    st.plotly_chart(
        _fx_history_figure(history),
        width="stretch",
        key="fx_engine_history_svg_v1",
    )
    with st.container(horizontal=True):
        st.metric("Calidad", quality.status, border=True)
        st.metric("Score de calidad", f"{quality.score:.0f}/100", border=True)
        st.metric("Observaciones", str(quality.observations), border=True)
        st.metric("Cobertura", f"{quality.coverage_ratio:.1%}", border=True)
        st.metric("Incidencias", str(len(quality.incidents)), border=True)
    st.caption(
        f"Proveedor: {history.route.provider} · Ruta: {history.route.calculation_path} · "
        f"Último cierre: {history.market_timestamp:%d/%m/%Y} · "
        f"Recepción UTC: {history.received_at:%d/%m/%Y %H:%M}"
    )
    if quality.incidents:
        with st.expander("Incidencias de calidad"):
            for incident in quality.incidents:
                st.warning(f"{incident.code}: {incident.message}")

    st.subheader(":material/link: Pares relacionados")
    with st.container(horizontal=True):
        for related in _related_fx_pairs(pair):
            st.button(
                f"Añadir {related.display}",
                icon=":material/add:",
                on_click=_add_fx_comparison_asset,
                args=(related.asset_id,),
                key=f"fx_related_{related.asset_id}",
            )
        st.button(
            f"Añadir {pair.display} al comparador",
            icon=":material/add_chart:",
            on_click=_add_fx_comparison_asset,
            args=(pair.asset_id,),
            key="fx_add_current_pair",
        )

    _render_fx_comparator(
        pair,
        history,
        FX_HORIZONS[horizon_label],
        market_settings,
        virtual_catalog,
        instrument_catalog,
    )


def render_forex_tab(
    market_settings: MarketConfig,
    instrument_catalog: pd.DataFrame | None = None,
) -> None:
    st.subheader(":material/currency_exchange: Motor FX")
    st.caption(
        "Construye pares directos, inversos y sintéticos con convención BASE/QUOTE, "
        "sin almacenar combinaciones redundantes."
    )
    _render_fx_engine_dashboard(market_settings, instrument_catalog)
