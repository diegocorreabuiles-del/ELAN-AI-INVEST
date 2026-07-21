from __future__ import annotations

import streamlit as st

from .safe import safe_render as safe_render


def configure_page() -> None:
    st.set_page_config(
        page_title="ELAN Quantum",
        page_icon=":material/finance_mode:",
        layout="wide",
    )
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
        [data-testid='stMetricValue'] {font-size: 1.75rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(version: str) -> None:
    st.title("ELAN Quantum", anchor=False)
    st.caption("Inteligencia cuantitativa para invertir con disciplina.")
    st.caption(f"v{version} · Simulación, no asesoramiento financiero")


def render_main_metrics(
    market_regime: str,
    average_score: float,
    risk_level: str,
    annual_volatility_pct: float,
    var_95_pct: float,
    capital: float,
) -> None:
    cols = st.columns(5)
    cols[0].metric("Régimen", market_regime)
    cols[1].metric("Score medio", f"{average_score:.1f}/100")
    cols[2].metric("Riesgo cartera", risk_level)
    cols[3].metric("Volatilidad", f"{annual_volatility_pct:.1f}%")
    cols[4].metric(
        "VaR 95% diario",
        f"{var_95_pct:.2f}%",
        f"€{capital * var_95_pct / 100:,.0f}",
    )
