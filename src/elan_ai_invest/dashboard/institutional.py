from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from elan_ai_invest.institutional import optimize_portfolio


_METHODS = {
    "Paridad de riesgo": "risk_parity",
    "Mínima varianza": "minimum_variance",
    "Máxima diversificación": "maximum_diversification",
    "Pesos iguales": "equal_weight",
}


def render_institutional_tab(prices: pd.DataFrame, capital: float):
    st.subheader("Portfolio Optimizer Institutional")
    st.caption("Asignación cuantitativa con restricciones de concentración.")

    method_label = st.selectbox("Método", list(_METHODS), key="institutional_method")
    max_weight_pct = st.slider(
        "Peso máximo por activo",
        min_value=10,
        max_value=50,
        value=25,
        step=5,
        key="institutional_max_weight",
    )

    try:
        result = optimize_portfolio(
            prices,
            method=_METHODS[method_label],
            max_weight=max_weight_pct / 100,
        )
    except ValueError as exc:
        st.info(str(exc))
        return

    a, b, c, d = st.columns(4)
    a.metric("Retorno anual estimado", f"{result.annual_return_pct:.1f}%")
    b.metric("Volatilidad estimada", f"{result.annual_volatility_pct:.1f}%")
    c.metric("Sharpe histórico", f"{result.sharpe:.2f}")
    d.metric("Diversificación", f"{result.diversification_ratio:.2f}x")

    allocation = result.weights.rename_axis("symbol").reset_index(name="weight")
    allocation["weight_pct"] = allocation["weight"] * 100
    allocation["amount_eur"] = allocation["weight"] * capital
    allocation = allocation.sort_values("weight", ascending=False).reset_index(drop=True)

    st.dataframe(
        allocation[["symbol", "weight_pct", "amount_eur"]],
        use_container_width=True,
        hide_index=True,
    )
    st.plotly_chart(
        px.pie(allocation, names="symbol", values="weight_pct", title=method_label),
        use_container_width=True,
    )
