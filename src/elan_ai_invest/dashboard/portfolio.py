import plotly.express as px
import streamlit as st

from elan_ai_invest.portfolio import build_portfolio, portfolio_equity_curve


def render_portfolio_tab(ranking, risk_report, prices, capital, settings):
    profile = st.selectbox("Perfil", ["conservador", "moderado", "agresivo"], index=1, key="portfolio_profile")
    plan = build_portfolio(ranking, risk_report.asset_risk, capital=capital, profile=profile, min_score=55.0, max_positions=8, max_position_pct=settings.risk.max_position_pct, min_cash_pct=20.0)
    cols = st.columns(4)
    cols[0].metric("Capital", f"€{capital:,.0f}")
    cols[1].metric("Invertido", f"{plan.invested_weight_pct:.1f}%")
    cols[2].metric("Liquidez", f"{plan.cash_weight_pct:.1f}%")
    cols[3].metric("Riesgo estimado", plan.risk_level)
    if plan.allocations.empty:
        st.info("No hay activos con score suficiente. ELAN mantiene liquidez.")
        return
    st.dataframe(plan.allocations, use_container_width=True, hide_index=True)
    pie_data = plan.allocations[["symbol", "weight_pct"]].copy()
    pie_data.loc[len(pie_data)] = ["CASH", plan.cash_weight_pct]
    st.plotly_chart(px.pie(pie_data, names="symbol", values="weight_pct", title="Distribución propuesta"), use_container_width=True)
    curve = portfolio_equity_curve(prices, plan.allocations, capital)
    if not curve.empty:
        st.plotly_chart(px.line(curve, title="Cartera simulada vs SPY"), use_container_width=True)
