import pandas as pd
import plotly.express as px
import streamlit as st

from elan_ai_invest.core.config import Settings
from elan_ai_invest.portfolio import build_portfolio, portfolio_equity_curve
from elan_ai_invest.risk import PortfolioRiskReport


def render_portfolio_tab(
    ranking: pd.DataFrame,
    risk_report: PortfolioRiskReport,
    prices: pd.DataFrame,
    capital: float,
    settings: Settings,
) -> None:
    profiles = ["conservador", "moderado", "agresivo"]
    configured_profile = settings.portfolio.profile.lower()
    if configured_profile not in profiles:
        configured_profile = "moderado"
    profile = st.selectbox(
        "Perfil",
        profiles,
        index=profiles.index(configured_profile),
        key="portfolio_profile",
    )
    plan = build_portfolio(
        ranking,
        risk_report.asset_risk,
        capital=capital,
        profile=profile,
        min_score=settings.portfolio.min_score,
        max_positions=settings.portfolio.max_positions,
        max_position_pct=settings.portfolio.max_position_pct,
        min_cash_pct=settings.portfolio.min_cash_pct,
    )
    cols = st.columns(4)
    cols[0].metric("Capital", f"€{capital:,.0f}")
    cols[1].metric("Invertido", f"{plan.invested_weight_pct:.1f}%")
    cols[2].metric("Liquidez", f"{plan.cash_weight_pct:.1f}%")
    cols[3].metric("Riesgo estimado", plan.risk_level)
    if plan.allocations.empty:
        st.info("No hay activos con score suficiente. ELAN mantiene liquidez.")
        return
    st.dataframe(plan.allocations, width="stretch", hide_index=True)
    pie_data = plan.allocations[["symbol", "weight_pct"]].copy()
    pie_data.loc[len(pie_data)] = ["CASH", plan.cash_weight_pct]
    st.plotly_chart(
        px.pie(pie_data, names="symbol", values="weight_pct", title="Distribución propuesta"),
        width="stretch",
    )
    curve = portfolio_equity_curve(prices, plan.allocations, capital)
    if not curve.empty:
        st.plotly_chart(px.line(curve, title="Cartera simulada vs SPY"), width="stretch")
