from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from elan_ai_invest.analysis import AssetType, classify_asset
from elan_ai_invest.core.bootstrap import build_core_engine
from elan_ai_invest.core.models import AnalysisRequest
from elan_ai_invest.dashboard import (
    clear_market_history_cache,
    configure_page,
    ensure_active_symbol,
    load_decision_analysis,
    render_backtesting_tab,
    render_decision_terminal,
    render_forex_tab,
    render_fundamental_tab,
    render_header,
    render_history_tab,
    render_institutional_tab,
    render_intelligence_tab,
    render_main_metrics,
    render_market_tab,
    render_news_events_tab,
    render_paper_trading_tab,
    render_portfolio_tab,
    render_primary_asset_selector,
    render_ranking_tab,
    render_risk_tab,
    render_system_tab,
    safe_render,
    set_active_symbol,
    show_safe_error,
)
from elan_ai_invest.fx import (
    build_virtual_fx_catalog,
    load_currency_registry,
    search_fx_pairs,
)
from elan_ai_invest.instruments import (
    ASSET_TYPE_LABELS,
    CRYPTO_ASSET_GROUP,
    CRYPTO_ASSET_TYPES,
    labels_by_symbol,
    load_instrument_catalog,
    normalize_custom_symbol,
    search_instruments,
)
from elan_ai_invest.paper_trading import PaperTradingEngine
from elan_ai_invest.risk import calculate_risk_report
from elan_ai_invest.storage import load_workspace_symbols, save_workspace_symbols

ROOT = Path(__file__).resolve().parent
configure_page()
VIEW_LABELS = (
    "Mercado",
    "Inteligencia",
    "Fundamental",
    "Noticias y eventos",
    "Ranking",
    "Riesgo",
    "Cartera",
    "Institucional",
    "Paper Trading",
    "Backtesting",
    "Histórico",
    "Divisas",
    "Sistema",
)


@st.cache_data(show_spinner=False)
def load_catalog(
    curated_path: Path,
    open_catalog_path: Path,
    currency_registry_path: Path,
    currency_registry_modified_ns: int,
) -> pd.DataFrame:
    del currency_registry_modified_ns
    return load_instrument_catalog(
        curated_path,
        open_catalog_path,
        currency_registry_path,
    )


try:
    ENGINE = build_core_engine(ROOT)
    DB_PATH = ROOT / ENGINE.settings.storage.database_path

    watchlist_path = ROOT / "config" / "watchlist.csv"
    watchlist = pd.read_csv(watchlist_path)
    required_columns = {"symbol", "name"}
    missing_columns = required_columns.difference(watchlist.columns)
    if missing_columns:
        raise ValueError("Faltan columnas en watchlist.csv: " + ", ".join(sorted(missing_columns)))
    currency_registry_path = ROOT / "config" / "currencies.csv"
    catalog = load_catalog(
        ROOT / "config" / "instruments.csv",
        ROOT / "config" / "catalog" / "adanos_tickers.csv.gz",
        currency_registry_path,
        currency_registry_path.stat().st_mtime_ns,
    )
    if catalog.empty:
        raise ValueError("El catálogo de instrumentos está vacío.")
    currency_registry = load_currency_registry(currency_registry_path)
    virtual_fx_catalog = build_virtual_fx_catalog(currency_registry)
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
catalog_labels.update(
    dict(zip(virtual_fx_catalog["asset_id"], virtual_fx_catalog["label"], strict=True))
)
name_map.update(dict(zip(virtual_fx_catalog["asset_id"], virtual_fx_catalog["name"], strict=True)))
default_symbols = [
    symbol
    for symbol in watchlist["symbol"].astype(str).str.upper().tolist()
    if symbol in catalog_labels
]


def _persist_workspace_symbols() -> None:
    save_workspace_symbols(DB_PATH, st.session_state.get("workspace_symbols", []))


persisted_symbols = load_workspace_symbols(DB_PATH)
st.session_state["workspace_symbols"] = (
    default_symbols if persisted_symbols is None else persisted_symbols
)
if persisted_symbols is None:
    _persist_workspace_symbols()

render_header(ENGINE.settings.app.version)
active_view = st.pills(
    "Navegación principal",
    VIEW_LABELS,
    default="Mercado",
    required=True,
    key="active_view",
    label_visibility="collapsed",
    width="stretch",
)
assert active_view is not None

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
    catalog_asset_types = sorted(value for value in catalog["asset_type"].unique() if value)
    asset_types = ["", CRYPTO_ASSET_GROUP, *catalog_asset_types]
    selected_asset_type = st.selectbox(
        "Tipo",
        asset_types,
        format_func=lambda value: ASSET_TYPE_LABELS.get(value, value) if value else "Todos",
        key="instrument_asset_type",
    )

    country_scope = catalog
    if selected_asset_type == CRYPTO_ASSET_GROUP:
        country_scope = country_scope.loc[country_scope["asset_type"].isin(CRYPTO_ASSET_TYPES)]
    elif selected_asset_type:
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
    if selected_asset_type == CRYPTO_ASSET_GROUP or "cbdc" in search_query.casefold():
        st.caption(
            "Las CBDC son dinero digital emitido por bancos centrales, no "
            "criptoactivos cotizados en Yahoo; se excluyen hasta disponer de una "
            "fuente oficial de seguimiento no negociable."
        )

    search_results = search_instruments(
        catalog,
        search_query,
        selected_asset_type or None,
        selected_country or None,
        selected_exchange or None,
        limit=100,
    )
    include_virtual_fx = (
        bool(search_query.strip())
        and selected_asset_type in {"", "Forex"}
        and not selected_country
        and selected_exchange in {"", "FX"}
    )
    if include_virtual_fx:
        fx_matches = search_fx_pairs(virtual_fx_catalog, search_query, limit=100)
        if not fx_matches.empty:
            fx_results = pd.DataFrame(
                {
                    "symbol": fx_matches["asset_id"],
                    "ticker": fx_matches["pair"],
                    "name": fx_matches["name"],
                    "asset_type": "Forex",
                    "country": "",
                    "country_code": "",
                    "exchange": "FX",
                    "isin": "",
                    "aliases": fx_matches["pair"],
                    "source": "ELAN virtual FX",
                    "_search": fx_matches["_search"],
                }
            )
            search_results = (
                pd.concat([fx_results, search_results], ignore_index=True)
                .drop_duplicates("symbol", keep="first")
                .head(100)
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
            _persist_workspace_symbols()
        set_active_symbol(st.session_state, result_symbol, current_symbols)

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
                    _persist_workspace_symbols()
                    catalog_labels[normalized_symbol] = f"{normalized_symbol} — Símbolo manual"
                set_active_symbol(st.session_state, normalized_symbol, current_symbols)

    workspace_options = list(st.session_state["workspace_symbols"])
    selected = st.multiselect(
        "Universo activo",
        workspace_options,
        format_func=lambda symbol: catalog_labels.get(symbol, symbol),
        key="workspace_symbols",
        on_change=_persist_workspace_symbols,
        help="Elimina aquí los instrumentos que no quieras analizar.",
    )
    st.caption("La lista se guarda automáticamente en este equipo.")
    period_labels = {
        "1mo": "1 mes",
        "3mo": "3 meses",
        "6mo": "6 meses",
        "1y": "1 año",
        "2y": "2 años",
        "5y": "5 años",
        "10y": "10 años",
        "max": "Máximo",
    }
    period_options = list(period_labels)
    configured_period = str(ENGINE.settings.market.period)
    if configured_period not in period_options:
        period_options.append(configured_period)
    requested_period = st.session_state.pop("market_period_request", None)
    if requested_period in period_options:
        st.session_state["analysis_period"] = requested_period
    if st.session_state.get("analysis_period") not in period_options:
        st.session_state["analysis_period"] = configured_period
    period = st.selectbox(
        "Horizonte histórico",
        period_options,
        key="analysis_period",
        format_func=lambda value: period_labels.get(value, value),
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
    clear_market_history_cache()

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
current_active = st.session_state.get("active_symbol")
preferred_active = ranking.iloc[0]["symbol"] if current_active not in selected else None
active_symbol = ensure_active_symbol(
    st.session_state,
    selected,
    preferred=preferred_active,
)
assert active_symbol is not None

active_symbol = render_primary_asset_selector(selected, catalog_labels)
assert active_symbol is not None

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
active_profile = classify_asset(active_symbol, catalog)
benchmark_history = (
    prices[active_profile.benchmark]
    if active_profile.benchmark in prices and active_profile.benchmark != active_symbol
    else None
)
terminal_quality = (
    analysis.quality.assets.get(active_symbol) if analysis.quality is not None else None
)
try:
    terminal_analysis = load_decision_analysis(
        active_profile,
        period=period,
        market_config=ENGINE.settings.market,
        quality=terminal_quality,
        benchmark_history=benchmark_history,
        market_regime=analysis.market_regime,
        annualisation_days=ENGINE.settings.risk.annualisation_days,
        error_count=int(active_symbol in analysis.errors),
    )
except Exception as exc:
    terminal_analysis = None
    show_safe_error(
        "La terminal de decisión no pudo completar el histórico del activo.",
        exc,
        context="app:decision-terminal",
    )

render_decision_terminal(
    terminal_analysis,
    ranking,
    active_symbol,
    catalog_labels,
)

if active_view == "Mercado":
    safe_render(
        "Mercado",
        render_market_tab,
        ranking,
        prices,
        selected,
        catalog_labels,
        ENGINE.settings.market,
        analysis.quality,
    )
elif active_view == "Inteligencia":
    safe_render("Inteligencia", render_intelligence_tab, ranking, selected)
elif active_view == "Fundamental":
    safe_render("Fundamental", render_fundamental_tab, ranking, selected)
elif active_view == "Noticias y eventos":
    safe_render(
        "Noticias y eventos",
        render_news_events_tab,
        ranking,
        ENGINE.settings.news,
        selected,
    )
elif active_view == "Ranking":
    safe_render("Ranking", render_ranking_tab, ranking, prices, selected)
elif active_view == "Riesgo":
    safe_render("Riesgo", render_risk_tab, risk_report, ranking, capital, ENGINE.settings)
elif active_view == "Cartera":
    portfolio_symbols = [
        symbol
        for symbol in prices.columns
        if classify_asset(symbol, catalog).asset_type is not AssetType.FOREX
    ]
    if not portfolio_symbols:
        st.info("Las divisas son de solo lectura y no participan en la cartera propuesta.")
    else:
        portfolio_prices = prices.loc[:, portfolio_symbols]
        portfolio_ranking = ranking.loc[ranking["symbol"].isin(portfolio_symbols)].copy()
        portfolio_risk_report = calculate_risk_report(
            portfolio_prices,
            annualisation_days=ENGINE.settings.risk.annualisation_days,
        )
        safe_render(
            "Cartera",
            render_portfolio_tab,
            portfolio_ranking,
            portfolio_risk_report,
            portfolio_prices,
            capital,
            ENGINE.settings,
        )
elif active_view == "Institucional":
    safe_render("Institucional", render_institutional_tab, prices, capital)
elif active_view == "Paper Trading":
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
elif active_view == "Backtesting":
    safe_render(
        "Backtesting",
        render_backtesting_tab,
        prices,
        ENGINE.settings.backtest,
        ENGINE.settings.market.benchmark,
    )
elif active_view == "Histórico":
    safe_render("Histórico", render_history_tab, ENGINE, DB_PATH, selected, period)
elif active_view == "Divisas":
    safe_render("Divisas", render_forex_tab, ENGINE.settings.market, catalog)
elif active_view == "Sistema":
    safe_render("Sistema", render_system_tab, ROOT, ENGINE.settings)

if analysis.errors:
    with st.expander("Errores parciales de descarga"):
        st.json(analysis.errors)
