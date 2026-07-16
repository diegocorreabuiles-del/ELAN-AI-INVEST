import streamlit as st

from elan_ai_invest.core.models import AnalysisRequest
from elan_ai_invest.storage import read_history


def render_history_tab(engine, db_path, selected, period):
    if st.button("Guardar fotografía actual"):
        engine.run_analysis(AnalysisRequest(symbols=list(selected), period=period, save_snapshot=True))
        st.success("Fotografía guardada.")
    history = read_history(db_path)
    st.info("Sin histórico todavía.") if history.empty else st.dataframe(history, use_container_width=True, hide_index=True)
