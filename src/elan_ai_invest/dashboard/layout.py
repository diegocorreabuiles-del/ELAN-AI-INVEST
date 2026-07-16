from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st


def configure_page() -> None:
    st.set_page_config(
        page_title="ELAN Quantum",
        page_icon="📈",
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
    st.title("ELAN Quantum")
    st.caption(
        f"AI Investment Platform · v{version} · "
        "simulación, no asesoramiento financiero"
    )


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


def safe_render(
    title: str,
    renderer: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> None:
    try:
        renderer(*args, **kwargs)
    except Exception as exc:
        st.error(f"No se pudo cargar {title}.")
        with st.expander("Detalle técnico"):
            st.exception(exc)
