from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from elan_ai_invest.core.bootstrap import build_core_engine
from elan_ai_invest.core.models import AnalysisRequest
from elan_ai_invest.dashboard import (
    configure_page,
    render_backtesting_tab,
    render_header,
    render_history_tab,
    render_main_metrics,
    render_market_tab,
    render_paper_trading_tab,
    render_portfolio_tab,
    render_ranking_tab,
    render_risk_tab,
    render_system_tab,
)
from elan_ai_invest.paper_trading import PaperTradingEngine
from elan_ai_invest.risk import calculate_risk_report


ROOT = Path(__file__).resolve().parent

configure_page()

ENGINE = build_core_engine(ROOT)
DB_PATH = ROOT / ENGINE.settings.storage.database_path

watchlist = pd.read_csv(
    ROOT / "config" / "watchlist.csv"
)

name_map = dict(
    zip(
        watchlist["symbol"],
        watchlist["name"],
        strict=True,
    )
)

version = ENGINE.settings.app.version

render_header(version)


with st.sidebar:
    st.header("Configuración")

    selected = st.multiselect(
        "Activos",
        options=watchlist["symbol"].tolist(),
        default=watchlist["symbol"].tolist(),
    )

    period = st.selectbox(
        "Historial",
        ["1y", "2y", "5y"],
        index=1,
    )

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


@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def run_analysis(
    symbols: tuple[str, ...],
    selected_period: str,
):
    request = AnalysisRequest(
        symbols=list(symbols),
        period=selected_period,
    )

    return ENGINE.run_analysis(request)


if refresh:
    run_analysis.clear()


with st.spinner(
    "ELAN analiza mercado y riesgo..."
):
    analysis = run_analysis(
        tuple(selected),
        period,
    )


prices = analysis.prices
ranking = analysis.ranking.copy()


if prices.empty or ranking.empty:
    st.error("No hay datos suficientes.")
    st.stop()


ranking["name"] = (
    ranking["symbol"]
    .map(name_map)
    .fillna(ranking["symbol"])
)


paper_engine = PaperTradingEngine(
    ROOT
    / ENGINE.settings.paper_trading.database_path,
    initial_capital=(
        ENGINE.settings.paper_trading.initial_capital
    ),
    commission_pct=(
        ENGINE.settings.paper_trading.commission_pct
    ),
    stop_loss_pct=(
        ENGINE.settings.paper_trading.stop_loss_pct
    ),
    max_open_positions=(
        ENGINE.settings.paper_trading.max_open_positions
    ),
)


latest_prices = {
    symbol: float(
        prices[symbol]
        .dropna()
        .iloc[-1]
    )
    for symbol in prices.columns
    if not prices[symbol].dropna().empty
}


risk_report = calculate_risk_report(
    prices,
    annualisation_days=(
        ENGINE.settings.risk.annualisation_days
    ),
)


render_main_metrics(
    market_regime=analysis.market_regime,
    average_score=analysis.average_score,
    risk_level=risk_report.risk_level,
    annual_volatility_pct=(
        risk_report.annual_volatility_pct
    ),
    var_95_pct=risk_report.var_95_pct,
    capital=capital,
)


(
    tab_market,
    tab_ranking,
    tab_risk,
    tab_portfolio,
    tab_paper,
    tab_backtest,
    tab_history,
    tab_system,
) = st.tabs(
    [
        "Mercado",
        "Ranking",
        "Riesgo",
        "Cartera",
        "Paper Trading",
        "Backtesting",
        "Histórico",
        "Sistema",
    ]
)


with tab_market:
    render_market_tab(
        ranking,
    )


with tab_ranking:
    render_ranking_tab(
        ranking,
        prices,
    )


with tab_risk:
    render_risk_tab(
        risk_report,
        ranking,
        capital,
        ENGINE.settings,
    )


with tab_portfolio:
    render_portfolio_tab(
        ranking,
        risk_report,
        prices,
        capital,
        ENGINE.settings,
    )


with tab_paper:
    render_paper_trading_tab(
        paper_engine,
        latest_prices,
        selected,
        ENGINE.settings,
    )


with tab_backtest:
    render_backtesting_tab(
        prices,
    )


with tab_history:
    render_history_tab(
        ENGINE,
        DB_PATH,
        selected,
        period,
    )


with tab_system:
    render_system_tab(
        ROOT,
        ENGINE.settings,
    )


if analysis.errors:
    with st.expander(
        "Errores de descarga"
    ):
        st.json(
            analysis.errors
        )