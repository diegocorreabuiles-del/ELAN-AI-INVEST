from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from elan_ai_invest.market_data import download_adjusted_close
from elan_ai_invest.scoring import score_assets

st.set_page_config(page_title="ELAN AI INVEST", layout="wide")
st.title("ELAN AI INVEST - Observador de mercado")
st.caption("Version 0.1: analisis educativo y paper trading. No envia ordenes reales.")

watchlist_path = ROOT / "config" / "watchlist.csv"
watchlist = pd.read_csv(watchlist_path)

with st.sidebar:
    st.header("Configuracion")
    selected = st.multiselect(
        "Activos a analizar",
        options=watchlist["symbol"].tolist(),
        default=watchlist["symbol"].tolist(),
    )
    period = st.selectbox("Historial", ["1y", "2y", "5y"], index=1)
    run = st.button("Actualizar analisis", type="primary")

if not selected:
    st.warning("Selecciona al menos un activo.")
    st.stop()

@st.cache_data(ttl=3600, show_spinner=False)
def load_data(symbols: tuple[str, ...], selected_period: str):
    return download_adjusted_close(symbols, selected_period)

if run or "result" not in st.session_state:
    with st.spinner("Descargando precios y calculando puntuaciones..."):
        st.session_state.result = load_data(tuple(selected), period)

result = st.session_state.result
prices = result.prices

if prices.empty:
    st.error("No se pudieron descargar datos.")
    if result.errors:
        st.json(result.errors)
    st.stop()

ranking = score_assets(prices)

c1, c2, c3 = st.columns(3)
c1.metric("Activos analizados", len(ranking))
c2.metric("Senales positivas", int((ranking["score"] >= 58).sum()) if not ranking.empty else 0)
c3.metric("Mejor puntuacion", f"{ranking['score'].max():.1f}" if not ranking.empty else "-")

st.subheader("Ranking cuantitativo")
st.dataframe(ranking, use_container_width=True, hide_index=True)

if not ranking.empty:
    best = ranking.iloc[0]["symbol"]
    chart_data = prices[[best]].dropna().reset_index()
    chart_data.columns = ["Fecha", "Precio"]
    fig = px.line(chart_data, x="Fecha", y="Precio", title=f"Evolucion de {best}")
    st.plotly_chart(fig, use_container_width=True)

if result.errors:
    with st.expander("Activos con errores"):
        st.json(result.errors)

st.info(
    "La puntuacion combina tendencia, momentum y volatilidad. "
    "No constituye asesoramiento financiero ni una prediccion garantizada."
)
