from collections.abc import Callable
from typing import ParamSpec, TypeVar

import streamlit as st

P = ParamSpec("P")
R = TypeVar("R")


def safe_render(
    title: str,
    renderer: Callable[P, R],
    *args: P.args,
    **kwargs: P.kwargs,
) -> R | None:
    """Render a dashboard section and contain failures at the UI boundary."""
    try:
        return renderer(*args, **kwargs)
    except Exception as exc:
        st.error(f"Error en {title}: {exc}")
        return None
