from collections.abc import Callable

import streamlit as st


def safe_render(
    title: str,
    renderer: Callable,
    *args,
    **kwargs,
):
    try:
        return renderer(*args, **kwargs)
    except Exception as exc:
        st.error(f"Error en {title}: {exc}")
        return None
