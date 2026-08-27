from pathlib import Path

import streamlit as st

from elan_ai_invest.core.config import Settings
from elan_ai_invest.system_status import collect_system_status


def render_system_tab(root: Path, settings: Settings) -> None:
    status = collect_system_status(root, settings)
    cols = st.columns(4)
    cols[0].metric("Versión", status.version)
    cols[1].metric("Python", status.python_version)
    cols[2].metric("Proveedor", status.market_provider)
    cols[3].metric("Entorno", status.environment)
    st.dataframe(status.as_dataframe(), width="stretch", hide_index=True)
    st.success("Sistema listo.") if status.ok else st.warning("Hay comprobaciones pendientes.")
