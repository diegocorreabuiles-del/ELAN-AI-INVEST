from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from elan_ai_invest.backtest import momentum_backtest, performance_stats
from elan_ai_invest.market_data import download_adjusted_close
from elan_ai_invest.scoring import score_assets
from elan_ai_invest.storage import read_history, save_snapshot

st.set_page_config(page_title="ELAN AI INVEST", page_icon="📈", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
[data-testid="stMetricValue"] {font-size: 1.8rem;}
.small-note {color:#6b7280;font-size:0.9rem;}
</style>
""", unsafe_allow_html=True)

DB_PATH = ROOT / "data" / "elan_ai_invest.db"
watchlist = pd.read_csv(ROOT / "config" / "watchlist.csv")
name_map = dict(zip(watchlist["symbol"], watchlist["name"]))

st.title("ELAN AI INVEST")
st.caption("Versión 0.2 · observador cuantitativo, histórico y backtesting educativo · sin órdenes reales")

with st.sidebar:
    st.header("Configuración")
    selected = st.multiselect(
        "Activos",
        options=watchlist["symbol"].tolist(),
        default=watchlist["symbol"].tolist(),
    )
    period = st.selectbox("Historial", ["1y", "2y", "5y"], index=1)
    refresh = st.button("Actualizar mercado", type="primary", use_container_width=True)
    st.divider()
    st.caption("Los datos se usan para investigación y pueden contener retrasos o ajustes.")

if not selected:
    st.warning("Selecciona al menos un activo.")
    st.stop()

@st.cache_data(ttl=3600, show_spinner=False)
def load_data(symbols: tuple[str, ...], selected_period: str):
    return download_adjusted_close(symbols, selected_period)

if refresh:
    load_data.clear()

with st.spinner("Descargando datos y calculando señales..."):
    result = load_data(tuple(selected), period)
prices = result.prices
if prices.empty:
    st.error("No se pudieron descargar datos de mercado.")
    if result.errors:
        st.json(result.errors)
    st.stop()

ranking = score_assets(prices)
if ranking.empty:
    st.error("No hay suficiente historial para calcular el ranking. Prueba con 2y o 5y.")
    st.stop()
ranking["name"] = ranking["symbol"].map(name_map).fillna(ranking["symbol"])

breadth = float(ranking["above_ma200"].mean() * 100)
avg_score = float(ranking["score"].mean())
market_state = "Alcista" if breadth >= 65 and avg_score >= 58 else "Mixto" if breadth >= 40 else "Defensivo"
risk = float(ranking["volatility_pct"].median())

m1, m2, m3, m4 = st.columns(4)
m1.metric("Régimen de mercado", market_state)
m2.metric("Activos sobre MM200", f"{breadth:.0f}%")
m3.metric("Score medio", f"{avg_score:.1f}/100")
m4.metric("Volatilidad mediana", f"{risk:.1f}%")

tab_market, tab_ranking, tab_backtest, tab_history = st.tabs(
    ["Mercado", "Ranking", "Backtesting", "Histórico"]
)

with tab_market:
    left, right = st.columns([1.15, 0.85])
    with left:
        st.subheader("Mapa de oportunidades")
        bubble = px.scatter(
            ranking,
            x="volatility_pct",
            y="score",
            size=ranking["return_3m_pct"].abs().clip(lower=1),
            hover_name="name",
            hover_data=["symbol", "signal", "confidence", "return_3m_pct"],
            labels={"volatility_pct": "Volatilidad anualizada (%)", "score": "Score"},
        )
        bubble.add_hline(y=60, line_dash="dash")
        st.plotly_chart(bubble, use_container_width=True)
    with right:
        st.subheader("Top 5")
        top = ranking.head(5).copy()
        for _, row in top.iterrows():
            st.markdown(
                f"**{row['symbol']} · {row['name']}**  \n"
                f"Score **{row['score']:.1f}** · Confianza {row['confidence']:.0f}% · "
                f"3 meses {row['return_3m_pct']:+.1f}% · Riesgo {row['volatility_pct']:.1f}%"
            )
            st.progress(int(row["score"]))
    st.subheader("Evolución normalizada")
    normalized = prices.ffill().dropna(how="all")
    normalized = normalized / normalized.iloc[0] * 100
    fig = px.line(normalized, labels={"value": "Base 100", "index": "Fecha", "variable": "Activo"})
    st.plotly_chart(fig, use_container_width=True)

with tab_ranking:
    st.subheader("Ranking cuantitativo V2")
    display_cols = [
        "symbol", "name", "score", "confidence", "signal", "price",
        "return_1m_pct", "return_3m_pct", "return_6m_pct",
        "volatility_pct", "drawdown_pct",
    ]
    st.dataframe(
        ranking[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"),
            "confidence": st.column_config.ProgressColumn("Confianza", min_value=0, max_value=100, format="%.1f%%"),
        },
    )
    chosen = st.selectbox("Ver detalle", ranking["symbol"].tolist())
    detail = ranking.loc[ranking["symbol"] == chosen].iloc[0]
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f"### {chosen} · {detail['name']}")
        st.metric("Score", f"{detail['score']:.1f}", detail["signal"])
        st.write(
            "La puntuación combina tendencia (40%), momentum (35%), volatilidad (15%) "
            "y control de drawdown (10%)."
        )
        reasons = []
        reasons.append("Cotiza sobre la media de 200 sesiones" if detail["above_ma200"] else "Cotiza bajo la media de 200 sesiones")
        reasons.append(f"Momentum a 3 meses: {detail['return_3m_pct']:+.1f}%")
        reasons.append(f"Volatilidad anualizada: {detail['volatility_pct']:.1f}%")
        reasons.append(f"Drawdown actual: {detail['drawdown_pct']:.1f}%")
        for reason in reasons:
            st.write("• " + reason)
    with c2:
        series = prices[chosen].dropna()
        chart = go.Figure()
        chart.add_trace(go.Scatter(x=series.index, y=series, name="Precio"))
        chart.add_trace(go.Scatter(x=series.index, y=series.rolling(50).mean(), name="MM50"))
        chart.add_trace(go.Scatter(x=series.index, y=series.rolling(200).mean(), name="MM200"))
        chart.update_layout(title=f"Precio y medias móviles · {chosen}", yaxis_title="Precio")
        st.plotly_chart(chart, use_container_width=True)

with tab_backtest:
    st.subheader("Backtest educativo de momentum")
    a, b, c = st.columns(3)
    lookback = a.selectbox("Ventana de momentum", [21, 63, 126], index=1)
    top_n = b.slider("Número de activos", 1, min(8, len(prices.columns)), min(3, len(prices.columns)))
    rebalance = c.selectbox("Rebalanceo", [5, 21, 63], index=1)
    bt = momentum_backtest(prices, lookback=lookback, top_n=top_n, rebalance=rebalance)
    if bt.empty:
        st.warning("No hay historial suficiente para esta configuración.")
    else:
        stats = performance_stats(bt["strategy"])
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Rentabilidad total", f"{stats['total_return_pct']:.1f}%")
        b2.metric("CAGR", f"{stats['cagr_pct']:.1f}%")
        b3.metric("Sharpe", f"{stats['sharpe']:.2f}")
        b4.metric("Drawdown máximo", f"{stats['max_drawdown_pct']:.1f}%")
        bt_chart = px.line(bt * 100, labels={"value": "Capital (base 100)", "index": "Fecha", "variable": "Serie"})
        st.plotly_chart(bt_chart, use_container_width=True)
        st.info("El backtest no incluye impuestos, spread, deslizamiento ni comisiones. No es una promesa de resultados futuros.")

with tab_history:
    st.subheader("Histórico local de análisis")
    if st.button("Guardar fotografía actual"):
        count = save_snapshot(DB_PATH, ranking, datetime.now().isoformat(timespec="seconds"))
        st.success(f"Se guardaron {count} registros en la base de datos local.")
    history = read_history(DB_PATH)
    if history.empty:
        st.info("Todavía no hay fotografías guardadas. Pulsa “Guardar fotografía actual”.")
    else:
        st.dataframe(history, use_container_width=True, hide_index=True)

if result.errors:
    with st.expander("Activos con errores de descarga"):
        st.json(result.errors)

st.divider()
st.caption("ELAN AI INVEST v0.2 · Herramienta educativa y de investigación. No constituye asesoramiento financiero.")
