from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from elan_ai_invest.fundamental import YahooFundamentalProvider, analyze_fundamentals


@st.cache_data(ttl=21600, max_entries=50, show_spinner=False)
def _load_fundamental(symbol: str):
    snapshot = YahooFundamentalProvider().get_snapshot(symbol)
    return analyze_fundamentals(snapshot)


def _format_large(value: float | None) -> str:
    if value is None:
        return "N/D"
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:,.1f} B"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.1f} M"
    return f"{value:,.0f}"


def render_fundamental_tab(ranking: pd.DataFrame):
    st.subheader("Fundamental Engine Institutional")
    st.caption("Calidad, crecimiento, valoración, balance y generación de caja.")

    symbol = st.selectbox(
        "Empresa",
        ranking["symbol"].tolist(),
        key="fundamental_symbol",
    )

    try:
        with st.spinner(f"Analizando fundamentales de {symbol}..."):
            analysis = _load_fundamental(symbol)
    except Exception as exc:
        st.error(f"No se pudieron obtener fundamentales para {symbol}: {exc}")
        return

    snapshot = analysis.snapshot
    st.markdown(f"### {snapshot.company_name} · {snapshot.symbol}")
    st.caption(" · ".join(part for part in [snapshot.sector, snapshot.industry] if part))

    a, b, c, d = st.columns(4)
    a.metric("Fundamental Score", f"{analysis.score:.1f}/100")
    b.metric("Confianza de datos", f"{analysis.confidence:.0f}%")
    c.metric("Decisión", analysis.decision)
    d.metric("Capitalización", _format_large(snapshot.market_cap))
    st.write(analysis.explanation)

    factor_data = pd.DataFrame(
        {
            "factor": ["Calidad", "Crecimiento", "Valoración", "Balance", "Caja"],
            "score": [
                analysis.quality_score,
                analysis.growth_score,
                analysis.valuation_score,
                analysis.balance_sheet_score,
                analysis.cash_flow_score,
            ],
        }
    )
    st.plotly_chart(
        px.bar(
            factor_data,
            x="score",
            y="factor",
            orientation="h",
            range_x=[0, 100],
            title="Descomposición fundamental",
        ),
        width="stretch",
    )

    metrics = pd.DataFrame(
        [
            ("PER histórico", snapshot.trailing_pe),
            ("PER esperado", snapshot.forward_pe),
            ("PEG", snapshot.peg_ratio),
            ("Precio/Valor contable", snapshot.price_to_book),
            ("EV/EBITDA", snapshot.enterprise_to_ebitda),
            ("ROE", snapshot.return_on_equity),
            ("ROA", snapshot.return_on_assets),
            ("Margen neto", snapshot.profit_margin),
            ("Margen operativo", snapshot.operating_margin),
            ("Crecimiento ingresos", snapshot.revenue_growth),
            ("Crecimiento beneficios", snapshot.earnings_growth),
            ("Deuda/Patrimonio", snapshot.debt_to_equity),
            ("Current ratio", snapshot.current_ratio),
            ("Flujo de caja libre", snapshot.free_cash_flow),
            ("Flujo de caja operativo", snapshot.operating_cash_flow),
            ("Rentabilidad dividendo", snapshot.dividend_yield),
        ],
        columns=["Métrica", "Valor"],
    )
    st.dataframe(metrics, width="stretch", hide_index=True)
