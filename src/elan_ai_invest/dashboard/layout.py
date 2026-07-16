import streamlit as st


def configure_page():
    st.set_page_config(
        page_title="ELAN Quantum",
        page_icon="📈",
        layout="wide",
    )

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.75rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(version: str):
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
):
    m1, m2, m3, m4, m5 = st.columns(5)

    m1.metric("Régimen", market_regime)
    m2.metric("Score medio", f"{average_score:.1f}/100")
    m3.metric("Riesgo cartera", risk_level)
    m4.metric("Volatilidad", f"{annual_volatility_pct:.1f}%")
    m5.metric(
        "VaR 95% diario",
        f"{var_95_pct:.2f}%",
        f"€{capital * var_95_pct / 100:,.0f}",
    )