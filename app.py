from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from elan_ai_invest.core.bootstrap import build_core_engine
from elan_ai_invest.core.models import AnalysisRequest
from elan_ai_invest.dashboard import (
    configure_page,
    render_backtesting_tab,
    render_fundamental_tab,
    render_header,
    render_history_tab,
    render_institutional_tab,
    render_intelligence_tab,
    render_main_metrics,
    render_market_tab,
    render_paper_trading_tab,
    render_portfolio_tab,
    render_ranking_tab,
    render_risk_tab,
    render_system_tab,
    safe_render,
    show_safe_error,
)
from elan_ai_invest.instruments import (
    ASSET_TYPE_LABELS,
    labels_by_symbol,
    load_instrument_catalog,
    normalize_custom_symbol,
    search_instruments,
)
from elan_ai_invest.paper_trading import PaperTradingEngine
from elan_ai_invest.risk import calculate_risk_report

ROOT = Path(__file__).resolve().parent
configure_page()


@st.cache_data(show_spinner=False)
def load_catalog(curated_path: Path, open_catalog_path: Path) -> pd.DataFrame:
    return load_instrument_catalog(curated_path, open_catalog_path)


try:
    ENGINE = build_core_engine(ROOT)
    DB_PATH = ROOT / ENGINE.settings.storage.database_path

    watchlist_path = ROOT / "config" / "watchlist.csv"
    watchlist = pd.read_csv(watchlist_path)
    required_columns = {"symbol", "name"}
    missing_columns = required_columns.difference(watchlist.columns)
    if missing_columns:
        raise ValueError("Faltan columnas en watchlist.csv: " + ", ".join(sorted(missing_columns)))
    catalog = load_catalog(
        ROOT / "config" / "instruments.csv",
        ROOT / "config" / "catalog" / "adanos_tickers.csv.gz",
    )
    if catalog.empty:
        raise ValueError("El catálogo de instrumentos está vacío.")
except Exception as exc:
    show_safe_error(
        "ELAN Quantum no pudo iniciar correctamente.",
        exc,
        context="app:startup",
    )
    st.info("Ejecuta update.bat y vuelve a abrir la aplicación.")
    st.stop()

catalog_labels = labels_by_symbol(catalog)
name_map = dict(zip(catalog["symbol"], catalog["name"], strict=True))
default_symbols = [
    symbol
    for symbol in watchlist["symbol"].astype(str).str.upper().tolist()
    if symbol in catalog_labels
]
if "workspace_symbols" not in st.session_state:
    st.session_state["workspace_symbols"] = default_symbols

render_header(ENGINE.settings.app.version)

with st.sidebar:
    st.subheader(":material/tune: Espacio de trabajo")
    st.caption(
        f"Busca entre {len(catalog):,} instrumentos por símbolo, nombre, ISIN, país o bolsa."
    )

    search_query = st.text_input(
        "Buscar instrumento",
        placeholder="Ej.: Tencent, EMAAR, ES0113900J37, Colombia...",
        icon=":material/search:",
        key="instrument_search_query",
    )
    asset_types = ["", *sorted(value for value in catalog["asset_type"].unique() if value)]
    selected_asset_type = st.selectbox(
        "Tipo",
        asset_types,
        format_func=lambda value: ASSET_TYPE_LABELS.get(value, value) if value else "Todos",
        key="instrument_asset_type",
    )

    country_scope = catalog
    if selected_asset_type:
        country_scope = country_scope.loc[country_scope["asset_type"].eq(selected_asset_type)]
    countries = ["", *sorted(value for value in country_scope["country"].unique() if value)]
    selected_country = st.selectbox(
        "País",
        countries,
        format_func=lambda value: value or "Todos",
        key="instrument_country",
    )

    exchange_scope = country_scope
    if selected_country:
        exchange_scope = exchange_scope.loc[exchange_scope["country"].eq(selected_country)]
    exchanges = ["", *sorted(value for value in exchange_scope["exchange"].unique() if value)]
    selected_exchange = st.selectbox(
        "Bolsa o mercado",
        exchanges,
        format_func=lambda value: value or "Todos",
        key="instrument_exchange",
    )

    search_results = search_instruments(
        catalog,
        search_query,
        selected_asset_type or None,
        selected_country or None,
        selected_exchange or None,
        limit=100,
    )
    result_symbols = search_results["symbol"].tolist()
    result_labels = labels_by_symbol(search_results)
    result_symbol = st.selectbox(
        "Resultados",
        result_symbols,
        index=0 if result_symbols else None,
        format_func=lambda symbol: result_labels.get(symbol, symbol),
        placeholder="No hay coincidencias",
        disabled=not result_symbols,
        key="instrument_search_result",
    )
    st.caption(
        f"{len(search_results)} coincidencias mostradas"
        + (" · Escribe más para afinar" if len(search_results) == 100 else "")
    )

    if st.button(
        "Añadir seleccionado",
        icon=":material/add:",
        width="stretch",
        disabled=result_symbol is None,
    ):
        current_symbols = list(st.session_state["workspace_symbols"])
        if result_symbol not in current_symbols:
            current_symbols.append(result_symbol)
            st.session_state["workspace_symbols"] = current_symbols

    with st.expander("Añadir símbolo manual de Yahoo"):
        custom_symbol = st.text_input(
            "Símbolo exacto",
            placeholder="Ej.: 1810.HK, SAN.MC, GC=F",
            key="custom_instrument_symbol",
        )
        if st.button("Añadir símbolo manual", width="stretch"):
            try:
                normalized_symbol = normalize_custom_symbol(custom_symbol)
            except ValueError as exc:
                st.error(str(exc))
            else:
                current_symbols = list(st.session_state["workspace_symbols"])
                if normalized_symbol not in current_symbols:
                    current_symbols.append(normalized_symbol)
                    st.session_state["workspace_symbols"] = current_symbols
                    catalog_labels[normalized_symbol] = f"{normalized_symbol} — Símbolo manual"

    workspace_options = list(st.session_state["workspace_symbols"])
    selected = st.multiselect(
        "Universo activo",
        workspace_options,
        format_func=lambda symbol: catalog_labels.get(symbol, symbol),
        key="workspace_symbols",
        help="Elimina aquí los instrumentos que no quieras analizar.",
    )
    period_options = ["1y", "2y", "5y"]
    if ENGINE.settings.market.period not in period_options:
        period_options.append(ENGINE.settings.market.period)
    period = st.selectbox(
        "Horizonte histórico",
        period_options,
        index=period_options.index(ENGINE.settings.market.period),
    )
    capital = st.number_input(
        "Capital simulado (€)",
        min_value=1_000.0,
        value=float(ENGINE.settings.portfolio.initial_capital),
        step=5_000.0,
    )
    refresh = st.button(
        "Actualizar datos",
        type="primary",
        icon=":material/refresh:",
        width="stretch",
    )
    st.caption(":green-badge[Paper trading] · Sin conexión a brokers")

if not selected:
    st.warning("Selecciona al menos un activo.")
    st.stop()


@st.cache_data(ttl=3600, max_entries=20, show_spinner=False)
def run_analysis(symbols: tuple[str, ...], selected_period: str):
    request = AnalysisRequest(
        symbols=list(symbols),
        period=selected_period,
    )
    return ENGINE.run_analysis(request)


if refresh:
    run_analysis.clear()

try:
    with st.spinner("Actualizando mercado y riesgo...", show_time=True):
        analysis = run_analysis(tuple(selected), period)
except Exception as exc:
    show_safe_error(
        "No se pudo completar el análisis de mercado.",
        exc,
        context="app:analysis",
    )
    st.info("Comprueba la conexión a internet y pulsa Actualizar mercado.")
    st.stop()

prices = analysis.prices
ranking = analysis.ranking.copy()

if prices.empty or ranking.empty:
    st.error("No hay datos suficientes para generar el análisis.")
    if analysis.errors:
        with st.expander("Errores de descarga"):
            st.json(analysis.errors)
    st.stop()

ranking["name"] = ranking["symbol"].map(name_map).fillna(ranking["symbol"])

latest_prices = {
    symbol: float(prices[symbol].dropna().iloc[-1])
    for symbol in prices.columns
    if not prices[symbol].dropna().empty
}

risk_report = calculate_risk_report(
    prices,
    annualisation_days=ENGINE.settings.risk.annualisation_days,
)

render_main_metrics(
    analysis.market_regime,
    analysis.average_score,
    risk_report.risk_level,
    risk_report.annual_volatility_pct,
    risk_report.var_95_pct,
    capital,
)

tabs = st.tabs(
    [
        "Mercado",
        "Inteligencia",
        "Fundamental",
        "Ranking",
        "Riesgo",
        "Cartera",
        "Institucional",
        "Paper Trading",
        "Backtesting",
        "Histórico",
        "Sistema",
    ],
    on_change="rerun",
)

if tabs[0].open:
    with tabs[0]:
        safe_render("Mercado", render_market_tab, ranking)
if tabs[1].open:
    with tabs[1]:
        safe_render("Inteligencia", render_intelligence_tab, ranking)
if tabs[2].open:
    with tabs[2]:
        safe_render("Fundamental", render_fundamental_tab, ranking)
if tabs[3].open:
    with tabs[3]:
        safe_render("Ranking", render_ranking_tab, ranking, prices)
if tabs[4].open:
    with tabs[4]:
        safe_render("Riesgo", render_risk_tab, risk_report, ranking, capital, ENGINE.settings)
if tabs[5].open:
    with tabs[5]:
        safe_render(
            "Cartera",
            render_portfolio_tab,
            ranking,
            risk_report,
            prices,
            capital,
            ENGINE.settings,
        )
if tabs[6].open:
    with tabs[6]:
        safe_render("Institucional", render_institutional_tab, prices, capital)
if tabs[7].open:
    with tabs[7]:
        paper_engine = None
        if ENGINE.settings.paper_trading.enabled:
            paper_engine = PaperTradingEngine(
                ROOT / ENGINE.settings.paper_trading.database_path,
                initial_capital=ENGINE.settings.paper_trading.initial_capital,
                commission_pct=ENGINE.settings.paper_trading.commission_pct,
                stop_loss_pct=ENGINE.settings.paper_trading.stop_loss_pct,
                max_open_positions=ENGINE.settings.paper_trading.max_open_positions,
            )
        safe_render(
            "Paper Trading",
            render_paper_trading_tab,
            paper_engine,
            latest_prices,
            selected,
            ENGINE.settings,
        )
if tabs[8].open:
    with tabs[8]:
        safe_render(
            "Backtesting",
            render_backtesting_tab,
            prices,
            ENGINE.settings.backtest,
            ENGINE.settings.market.benchmark,
        )
if tabs[9].open:
    with tabs[9]:
        safe_render("Histórico", render_history_tab, ENGINE, DB_PATH, selected, period)
if tabs[10].open:
    with tabs[10]:
        safe_render("Sistema", render_system_tab, ROOT, ENGINE.settings)

if analysis.errors:
    with st.expander("Errores parciales de descarga"):
        st.json(analysis.errors)
