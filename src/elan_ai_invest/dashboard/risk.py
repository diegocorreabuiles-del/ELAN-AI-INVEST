import plotly.express as px
import streamlit as st

from elan_ai_invest.risk import suggested_position_size_pct


def render_risk_tab(risk_report, ranking, capital, settings):
    st.subheader("Risk Engine")

    r1, r2, r3, r4, r5 = st.columns(5)
    r1.metric("VaR 95%", f"{risk_report.var_95_pct:.2f}%")
    r2.metric("CVaR 95%", f"{risk_report.cvar_95_pct:.2f}%")
    r3.metric("VaR 99%", f"{risk_report.var_99_pct:.2f}%")
    r4.metric("Drawdown máximo", f"{risk_report.max_drawdown_pct:.1f}%")
    r5.metric("Diversificación", f"{risk_report.diversification_ratio:.2f}x")

    risk_table = risk_report.asset_risk.merge(
        ranking[["symbol", "score"]],
        on="symbol",
        how="left",
    )

    risk_table["suggested_position_pct"] = risk_table["volatility_pct"].apply(
        lambda value: suggested_position_size_pct(
            value,
            risk_budget_pct=settings.risk.risk_budget_per_position_pct,
            max_position_pct=settings.risk.max_position_pct,
        )
    )

    risk_table["suggested_amount_eur"] = (
        risk_table["suggested_position_pct"] / 100 * capital
    )

    st.dataframe(
        risk_table,
        use_container_width=True,
        hide_index=True,
    )

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
        labels={
            "risk_contribution_pct": "% riesgo",
            "symbol": "Activo",
        },
    )
    st.plotly_chart(contribution, use_container_width=True)