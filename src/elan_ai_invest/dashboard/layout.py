from __future__ import annotations

import math

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


def _format_context_number(value, *, suffix: str = "", decimals: int = 1) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "N/D"
    if not math.isfinite(numeric):
        return "N/D"
    return f"{numeric:,.{decimals}f}{suffix}"


def render_active_asset_context(
    ranking,
    active_symbol: str,
    labels=None,
    *,
    trailing_pe: float | None = None,
) -> None:
    matches = ranking.loc[ranking["symbol"].eq(active_symbol)]
    row = matches.iloc[0] if not matches.empty else None
    name = row.get("name", active_symbol) if row is not None else active_symbol
    if labels and row is None:
        name = labels.get(active_symbol, active_symbol)
    signal = "N/D" if row is None else row.get("signal", row.get("decision", "N/D"))

    with st.container(horizontal=True, gap="xsmall"):
        st.metric("Activo conectado", f"{active_symbol} · {name}", border=True)
        st.metric(
            "Precio",
            "N/D" if row is None else _format_context_number(row.get("price"), decimals=2),
            border=True,
        )
        st.metric("PER histórico", _format_context_number(trailing_pe, suffix="x"), border=True)
        st.metric(
            "Score",
            "N/D" if row is None else _format_context_number(row.get("score"), suffix="/100"),
            border=True,
        )
        st.metric("Señal", str(signal or "N/D"), border=True)
        st.metric(
            "Volatilidad",
            "N/D" if row is None else _format_context_number(row.get("volatility_pct"), suffix="%"),
            border=True,
        )
