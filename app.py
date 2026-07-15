from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from elan_ai_invest.backtest import momentum_backtest, performance_stats
from elan_ai_invest.core.bootstrap import build_core_engine
from elan_ai_invest.core.models import AnalysisRequest
from elan_ai_invest.risk import calculate_risk_report, suggested_position_size_pct
from elan_ai_invest.storage import read_history

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="ELAN Quantum", page_icon="📈", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
[data-testid="stMetricValue"] {font-size: 1.75rem;}
</style>
""",
    unsafe_allow_html=True,
)

ENGINE = build_core_engine(ROOT)
DB_PATH = ROOT / ENGINE.settings.storage.database_path
watchlist = pd.read_csv(ROOT / "config" / "watchlist.csv")
name_map = dict(zip(watchlist["symbol"], watchlist["name"]))

st.title("ELAN Quantum")
st.caption("AI Investment Platform · v0.4 Risk Engine · investigación, no asesoramiento financiero")

with st.sidebar:
    st.header("Configuración")
    selected = st.multiselect(
        "Activos",
        options=watchlist["symbol"].tolist(),
        default=watchlist["symbol"].tolist(),
    )
    period = st.selectbox("Historial", ["1y", "2y", "5y"], index=1)
    capital = st.number_input("Capital simulado (€)", min_value=1_000.0, value=100_000.0, step=5_000.0)
    refresh = st.button("Actualizar mercado", type="primary", use_container_width=True)

if not selected:
    st.warning("Selecciona al menos un activo.")
    st.stop()

@st.cache_data(ttl=3600, show_spinner=False)
def run_analysis(symbols: tuple[str, ...], selected_period: str):
    return ENGINE.run_analysis(AnalysisRequest(symbols=list(symbols), period=selected_period))

if refresh:
    run_analysis.clear()

with st.spinner("ELAN analiza mercado y riesgo..."):
    analysis = run_analysis(tuple(selected), period)

prices = analysis.prices
ranking = analysis.ranking.copy()
if prices.empty or ranking.empty:
    st.error("No hay datos suficientes.")
    st.stop()
ranking["name"] = ranking["symbol"].map(name_map).fillna(ranking["symbol"])

risk_report = calculate_risk_report(
    prices,
    annualisation_days=ENGINE.settings.risk.annualisation_days,
)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Régimen", analysis.market_regime)
m2.metric("Score medio", f"{analysis.average_score:.1f}/100")
m3.metric("Riesgo cartera", risk_report.risk_level)
m4.metric("Volatilidad", f"{risk_report.annual_volatility_pct:.1f}%")
m5.metric("VaR 95% diario", f"{risk_report.var_95_pct:.2f}%", f"€{capital * risk_report.var_95_pct / 100:,.0f}")

tab_market, tab_ranking, tab_risk, tab_backtest, tab_history = st.tabs(
    ["Mercado", "Ranking", "Riesgo", "Backtesting", "Histórico"]
)

with tab_market:
    left, right = st.columns([1.2, 0.8])
    with left:
        bubble = px.scatter(
            ranking,
            x="volatility_pct",
            y="score",
            size=ranking["return_3m_pct"].abs().clip(lower=1),
            hover_name="name",
            hover_data=["symbol", "signal", "confidence", "return_3m_pct"],
            labels={"volatility_pct": "Volatilidad (%)", "score": "Score"},
            title="Mapa de oportunidades",
        )
        bubble.add_hline(y=60, line_dash="dash")
        st.plotly_chart(bubble, use_container_width=True)
    with right:
        st.subheader("Top 5")
        for _, row in ranking.head(5).iterrows():
            st.markdown(
                f"**{row['symbol']} · {row['name']}**  \n"
                f"Score **{row['score']:.1f}** · 3m {row['return_3m_pct']:+.1f}% · "
                f"Vol. {row['volatility_pct']:.1f}%"
            )
            st.progress(int(row["score"]))

with tab_ranking:
    st.dataframe(
        ranking[["symbol", "name", "score", "confidence", "signal", "price", "return_3m_pct", "volatility_pct", "drawdown_pct"]],
        use_container_width=True,
        hide_index=True,
    )
    chosen = st.selectbox("Detalle", ranking["symbol"].tolist())
    series = prices[chosen].dropna()
    chart = go.Figure()
    chart.add_trace(go.Scatter(x=series.index, y=series, name="Precio"))
    chart.add_trace(go.Scatter(x=series.index, y=series.rolling(50).mean(), name="MM50"))
    chart.add_trace(go.Scatter(x=series.index, y=series.rolling(200).mean(), name="MM200"))
    st.plotly_chart(chart, use_container_width=True)

with tab_risk:
    st.subheader("Risk Engine")
    r1, r2, r3, r4, r5 = st.columns(5)
    r1.metric("VaR 95%", f"{risk_report.var_95_pct:.2f}%")
    r2.metric("CVaR 95%", f"{risk_report.cvar_95_pct:.2f}%")
    r3.metric("VaR 99%", f"{risk_report.var_99_pct:.2f}%")
    r4.metric("Drawdown máximo", f"{risk_report.max_drawdown_pct:.1f}%")
    r5.metric("Diversificación", f"{risk_report.diversification_ratio:.2f}x")

    st.caption("VaR/CVaR históricos diarios. La cartera simulada usa pesos iguales.")
    risk_table = risk_report.asset_risk.merge(
        ranking[["symbol", "score"]], on="symbol", how="left"
    )
    risk_table["suggested_position_pct"] = risk_table["volatility_pct"].apply(
        lambda value: suggested_position_size_pct(
            value,
            risk_budget_pct=ENGINE.settings.risk.risk_budget_per_position_pct,
            max_position_pct=ENGINE.settings.risk.max_position_pct,
        )
    )
    risk_table["suggested_amount_eur"] = risk_table["suggested_position_pct"] / 100 * capital
    st.dataframe(risk_table, use_container_width=True, hide_index=True)

    st.subheader("Correlaciones")
    heatmap = px.imshow(
        risk_report.correlation,
        text_auto=".2f",
        zmin=-1,
        zmax=1,
        aspect="auto",
    )
    st.plotly_chart(heatmap, use_container_width=True)

    st.subheader("Contribución al riesgo")
    contribution = px.bar(
        risk_table,
        x="symbol",
        y="risk_contribution_pct",
        labels={"risk_contribution_pct": "% riesgo", "symbol": "Activo"},
    )
    st.plotly_chart(contribution, use_container_width=True)

with tab_backtest:
    a, b, c = st.columns(3)
    lookback = a.selectbox("Momentum", [21, 63, 126], index=1)
    top_n = b.slider("Número de activos", 1, min(8, len(prices.columns)), min(3, len(prices.columns)))
    rebalance = c.selectbox("Rebalanceo", [5, 21, 63], index=1)
    bt = momentum_backtest(prices, lookback=lookback, top_n=top_n, rebalance=rebalance)
    if not bt.empty:
        stats = performance_stats(bt["strategy"])
        cols = st.columns(4)
        cols[0].metric("Rentabilidad", f"{stats['total_return_pct']:.1f}%")
        cols[1].metric("CAGR", f"{stats['cagr_pct']:.1f}%")
        cols[2].metric("Sharpe", f"{stats['sharpe']:.2f}")
        cols[3].metric("Drawdown", f"{stats['max_drawdown_pct']:.1f}%")
        st.plotly_chart(px.line(bt * 100), use_container_width=True)

with tab_history:
    if st.button("Guardar fotografía actual"):
        ENGINE.run_analysis(AnalysisRequest(symbols=list(selected), period=period, save_snapshot=True))
        st.success("Fotografía guardada.")
    history = read_history(DB_PATH)
    if history.empty:
        st.info("Sin histórico todavía.")
    else:
        st.dataframe(history, use_container_width=True, hide_index=True)

if analysis.errors:
    with st.expander("Errores de descarga"):
        st.json(analysis.errors)
