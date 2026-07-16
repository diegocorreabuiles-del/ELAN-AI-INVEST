import streamlit as st

from elan_ai_invest.system_status import collect_system_status


def render_system_tab(root, settings):

    st.subheader("Estado del sistema")

    status = collect_system_status(
        root,
        settings,
    )

    s1, s2, s3, s4 = st.columns(4)

    s1.metric("Versión", status.version)
    s2.metric("Python", status.python_version)
    s3.metric("Proveedor", status.market_provider)
    s4.metric("Entorno", status.environment)

    st.dataframe(
        status.as_dataframe(),
        use_container_width=True,
        hide_index=True,
    )

    if status.ok:
        st.success("Sistema listo.")
    else:
        st.warning("Hay comprobaciones pendientes.")