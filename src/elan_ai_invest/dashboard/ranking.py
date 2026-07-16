import plotly.graph_objects as go
import streamlit as st


def render_ranking_tab(ranking, prices):
    columns = [c for c in ["symbol", "name", "score", "confidence", "signal", "price", "return_3m_pct", "volatility_pct", "drawdown_pct"] if c in ranking.columns]
    st.dataframe(ranking[columns], use_container_width=True, hide_index=True)
    chosen = st.selectbox("Detalle", ranking["symbol"].tolist(), key="ranking_detail_symbol")
    series = prices[chosen].dropna()
    chart = go.Figure()
    chart.add_trace(go.Scatter(x=series.index, y=series, name="Precio"))
    chart.add_trace(go.Scatter(x=series.index, y=series.rolling(50).mean(), name="MM50"))
    chart.add_trace(go.Scatter(x=series.index, y=series.rolling(200).mean(), name="MM200"))
    st.plotly_chart(chart, use_container_width=True)
