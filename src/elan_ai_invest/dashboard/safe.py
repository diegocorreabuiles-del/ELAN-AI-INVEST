import logging
import secrets
from collections.abc import Callable
from typing import ParamSpec, TypeVar

import streamlit as st

P = ParamSpec("P")
R = TypeVar("R")
LOGGER = logging.getLogger("elan_ai_invest.dashboard")


def show_safe_error(message: str, exc: BaseException, *, context: str) -> str:
    """Log technical details and expose only a correlation reference in the UI."""
    error_id = secrets.token_hex(6).upper()
    LOGGER.exception("%s failed [error_id=%s]", context, error_id, exc_info=exc)
    st.error(f"{message} Referencia: `{error_id}`.")
    return error_id


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
        show_safe_error(
            f"No se pudo mostrar {title}.",
            exc,
            context=f"dashboard:{title}",
        )
        return None
