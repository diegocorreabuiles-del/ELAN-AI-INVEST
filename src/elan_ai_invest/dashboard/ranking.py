from collections.abc import Sequence
from functools import partial

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .workspace import (
    activate_from_table,
    activate_from_widget,
    symbol_options,
    sync_widget_to_active,
)


def render_ranking_tab(
    ranking: pd.DataFrame,
    prices: pd.DataFrame,
    workspace_symbols: Sequence[object] | None = None,
) -> None:
    columns = [
        c
        for c in [
            "symbol",
            "name",
            "score",
            "confidence",
            "signal",
            "price",
            "return_3m_pct",
            "volatility_pct",
            "drawdown_pct",
        ]
        if c in ranking.columns
    ]
    table_symbols = symbol_options(ranking["symbol"].tolist())
    st.dataframe(
        ranking[columns],
        width="stretch",
        hide_index=True,
        key="ranking_asset_table",
        on_select=partial(
            activate_from_table,
            "ranking_asset_table",
            tuple(table_symbols),
        ),
        selection_mode="single-row",
    )

    options = symbol_options(workspace_symbols if workspace_symbols is not None else table_symbols)
    sync_widget_to_active(st.session_state, "ranking_detail_symbol", options)
    chosen = st.selectbox(
        "Detalle",
        options,
        key="ranking_detail_symbol",
        on_change=activate_from_widget,
        args=("ranking_detail_symbol", tuple(options)),
    )
    if chosen not in prices or prices[chosen].dropna().empty:
        st.info(f"{chosen} no dispone de precios en el análisis actual.")
        return

    series = prices[chosen].dropna()
    chart = go.Figure()
    chart.add_trace(go.Scatter(x=series.index, y=series, name="Precio"))
    chart.add_trace(go.Scatter(x=series.index, y=series.rolling(50).mean(), name="MM50"))
    chart.add_trace(go.Scatter(x=series.index, y=series.rolling(200).mean(), name="MM200"))
    st.plotly_chart(chart, width="stretch")
