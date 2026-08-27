from collections.abc import Sequence
from functools import partial

import pandas as pd
import plotly.express as px
import streamlit as st

from .workspace import (
    activate_from_table,
    activate_from_widget,
    symbol_options,
    sync_widget_to_active,
)


def render_intelligence_tab(
    ranking: pd.DataFrame,
    workspace_symbols: Sequence[object] | None = None,
) -> None:
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
    table_symbols = symbol_options(ranking["symbol"].tolist())
    st.dataframe(
        ranking[available],
        width="stretch",
        hide_index=True,
        key="intelligence_asset_table",
        on_select=partial(
            activate_from_table,
            "intelligence_asset_table",
            tuple(table_symbols),
        ),
        selection_mode="single-row",
    )

    options = symbol_options(workspace_symbols if workspace_symbols is not None else table_symbols)
    sync_widget_to_active(st.session_state, "professional_intelligence_symbol", options)
    selected = st.selectbox(
        "Explicación profesional",
        options,
        key="professional_intelligence_symbol",
        on_change=activate_from_widget,
        args=("professional_intelligence_symbol", tuple(options)),
    )
    matches = ranking.loc[ranking["symbol"] == selected]
    if matches.empty:
        st.info(f"{selected} no dispone de scoring en el análisis actual.")
        return

    row = matches.iloc[0]
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
    st.plotly_chart(chart, width="stretch")
