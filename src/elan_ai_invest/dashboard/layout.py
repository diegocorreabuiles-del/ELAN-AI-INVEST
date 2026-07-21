from __future__ import annotations

import streamlit as st

from .safe import safe_render as safe_render


def configure_page() -> None:
    st.set_page_config(
        page_title="ELAN Quantum",
        page_icon=":material/finance_mode:",
        layout="wide",
        initial_sidebar_state="auto",
    )


def render_header(version: str) -> None:
    with st.container(
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
        gap="small",
    ):
        st.title("ELAN Quantum", anchor=False)
        st.badge("Datos de mercado", icon=":material/query_stats:", color="green")
        st.badge("Solo simulación", icon=":material/shield:", color="gray")
        st.badge(f"v{version}", color="blue")
    st.caption("Centro cuantitativo para analizar mercado, riesgo y cartera en un solo espacio.")


def render_main_metrics(
    market_regime: str,
    average_score: float,
    risk_level: str,
    annual_volatility_pct: float,
    var_95_pct: float,
    capital: float,
) -> None:
    with st.container(horizontal=True, gap="xsmall"):
        st.metric("Régimen", market_regime, border=True)
        st.metric("Score medio", f"{average_score:.1f}/100", border=True)
        st.metric("Riesgo cartera", risk_level, border=True)
        st.metric("Volatilidad", f"{annual_volatility_pct:.1f}%", border=True)
        st.metric(
            "VaR 95% diario",
            f"{var_95_pct:.2f}%",
            f"€{capital * var_95_pct / 100:,.0f}",
            delta_color="inverse",
            border=True,
        )
