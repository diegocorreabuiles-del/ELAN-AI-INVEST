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
)
from elan_ai_invest.paper_trading import PaperTradingEngine
from elan_ai_invest.risk import calculate_risk_report

ROOT = Path(__file__).resolve().parent
configure_page()

try:
    ENGINE = build_core_engine(ROOT)
    DB_PATH = ROOT / ENGINE.settings.storage.database_path

    watchlist_path = ROOT / "config" / "watchlist.csv"
    watchlist = pd.read_csv(watchlist_path)
    required_columns = {"symbol", "name"}
    missing_columns = required_columns.difference(watchlist.columns)
    if missing_columns:
        raise ValueError(
            "Faltan columnas en watchlist.csv: " + ", ".join(sorted(missing_columns))
        )
except Exception as exc:
    st.error("ELAN Quantum no pudo iniciar correctamente.")
    st.info("Ejecuta update.bat y vuelve a abrir la aplicación.")
    with st.expander("Detalle técnico"):
        st.exception(exc)
    st.stop()

name_map = dict(zip(watchlist["symbol"], watchlist["name"], strict=True))
render_header(ENGINE.settings.app.version)

with st.sidebar:
    st.header("Configuración")
    selected = st.multiselect(
        "Activos",
        watchlist["symbol"].tolist(),
        default=watchlist["symbol"].tolist(),
    )
    period = st.selectbox("Historial", ["1y", "2y", "5y"], index=1)
    capital = st.number_input(
        "Capital simulado (€)",
        min_value=1_000.0,
        value=100_000.0,
        step=5_000.0,
    )
    refresh = st.button(
        "Actualizar mercado",
        type="primary",
        use_container_width=True,
    )

if not selected:
    st.warning("Selecciona al menos un activo.")
    st.stop()


@st.cache_data(ttl=3600, show_spinner=False)
def run_analysis(symbols: tuple[str, ...], selected_period: str):
    request = AnalysisRequest(
        symbols=list(symbols),
        period=selected_period,
    )
    return ENGINE.run_analysis(request)


if refresh:
    run_analysis.clear()

try:
    with st.spinner("ELAN analiza mercado y riesgo..."):
        analysis = run_analysis(tuple(selected), period)
except Exception as exc:
    st.error("No se pudo completar el análisis de mercado.")
    st.info("Comprueba la conexión a internet y pulsa Actualizar mercado.")
    with st.expander("Detalle técnico"):
        st.exception(exc)
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

paper_engine = PaperTradingEngine(
    ROOT / ENGINE.settings.paper_trading.database_path,
    initial_capital=ENGINE.settings.paper_trading.initial_capital,
    commission_pct=ENGINE.settings.paper_trading.commission_pct,
    stop_loss_pct=ENGINE.settings.paper_trading.stop_loss_pct,
    max_open_positions=ENGINE.settings.paper_trading.max_open_positions,
)

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
    ]
)

with tabs[0]:
    safe_render("Mercado", render_market_tab, ranking)
with tabs[1]:
    safe_render("Inteligencia", render_intelligence_tab, ranking)
with tabs[2]:
    safe_render("Fundamental", render_fundamental_tab, ranking)
with tabs[3]:
    safe_render("Ranking", render_ranking_tab, ranking, prices)
with tabs[4]:
    safe_render("Riesgo", render_risk_tab, risk_report, ranking, capital, ENGINE.settings)
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
with tabs[6]:
    safe_render("Institucional", render_institutional_tab, prices, capital)
with tabs[7]:
    safe_render(
        "Paper Trading",
        render_paper_trading_tab,
        paper_engine,
        latest_prices,
        selected,
        ENGINE.settings,
    )
with tabs[8]:
    safe_render("Backtesting", render_backtesting_tab, prices)
with tabs[9]:
    safe_render("Histórico", render_history_tab, ENGINE, DB_PATH, selected, period)
with tabs[10]:
    safe_render("Sistema", render_system_tab, ROOT, ENGINE.settings)

if analysis.errors:
    with st.expander("Errores parciales de descarga"):
        st.json(analysis.errors)
