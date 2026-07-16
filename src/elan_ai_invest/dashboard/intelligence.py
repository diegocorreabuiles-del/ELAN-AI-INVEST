import plotly.express as px
import streamlit as st


def render_intelligence_tab(ranking):
    st.subheader("Intelligence Engine Professional")
    st.caption("Ranking multifactor: tendencia, momentum, fuerza relativa y riesgo ajustado.")

    columns = [
        "symbol",
        "name",
        "decision",
        "score",
        "confidence",
        "trend_factor",
        "momentum_factor",
        "relative_strength_factor",
        "risk_adjusted_factor",
        "trend_quality_factor",
    ]
    available = [column for column in columns if column in ranking.columns]
    st.dataframe(ranking[available], use_container_width=True, hide_index=True)

    selected = st.selectbox(
        "Explicación profesional",
        ranking["symbol"].tolist(),
        key="professional_intelligence_symbol",
    )
    row = ranking.loc[ranking["symbol"] == selected].iloc[0]
    left, right = st.columns([0.65, 0.35])
    with left:
        st.markdown(f"### {selected} · {row.get('name', selected)}")
        st.markdown(f"**Decisión:** {row.get('decision', 'NEUTRAL')}")
        st.write(row.get("explanation", "Sin explicación disponible."))
    with right:
        st.metric("Score profesional", f"{row['score']:.1f}/100")
        st.metric("Confianza", f"{row['confidence']:.1f}%")

    factor_columns = [
        "trend_factor",
        "momentum_factor",
        "relative_strength_factor",
        "risk_adjusted_factor",
        "trend_quality_factor",
    ]
    factor_labels = {
        "trend_factor": "Tendencia",
        "momentum_factor": "Momentum",
        "relative_strength_factor": "Fuerza relativa",
        "risk_adjusted_factor": "Riesgo ajustado",
        "trend_quality_factor": "Calidad tendencia",
    }
    factor_data = [
        {"factor": factor_labels[column], "score": float(row.get(column, 0))}
        for column in factor_columns
    ]
    chart = px.bar(
        factor_data,
        x="score",
        y="factor",
        orientation="h",
        range_x=[0, 100],
        title="Descomposición multifactor",
    )
    st.plotly_chart(chart, use_container_width=True)
