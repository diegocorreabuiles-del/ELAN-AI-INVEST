from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from elan_ai_invest.dashboard.layout import safe_render as layout_safe_render
from elan_ai_invest.dashboard.market import ComparisonData, _comparison_figures
from elan_ai_invest.dashboard.safe import safe_render

ROOT = Path(__file__).resolve().parents[1]


def test_all_dashboard_views_are_lazy() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")

    assert "active_view = st.pills(" in source
    assert "required=True" in source
    guarded_views = set(re.findall(r'(?:if|elif) active_view == "([^"]+)":', source))
    assert guarded_views == {
        "Mercado",
        "Inteligencia",
        "Fundamental",
        "Noticias y eventos",
        "Ranking",
        "Riesgo",
        "Cartera",
        "Institucional",
        "Paper Trading",
        "Backtesting",
        "Histórico",
        "Divisas",
        "Sistema",
    }
    assert "st.tabs(" not in source


def test_deprecated_streamlit_width_api_is_absent() -> None:
    python_files = [ROOT / "app.py", *(ROOT / "src").rglob("*.py")]

    offenders = [
        str(path.relative_to(ROOT))
        for path in python_files
        if "use_container_width" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_safe_render_has_one_public_implementation() -> None:
    assert layout_safe_render is safe_render


def test_connected_asset_tables_use_native_single_row_selection() -> None:
    dashboard_root = ROOT / "src" / "elan_ai_invest" / "dashboard"
    for filename in ("intelligence.py", "ranking.py"):
        source = (dashboard_root / filename).read_text(encoding="utf-8")
        assert "on_select=partial(" in source
        assert 'selection_mode="single-row"' in source


def test_market_local_controls_are_fragment_scoped() -> None:
    source = (ROOT / "src" / "elan_ai_invest" / "dashboard" / "market.py").read_text(
        encoding="utf-8"
    )

    assert "@st.fragment\ndef _render_history_detail" in source
    assert "@st.fragment\ndef _render_comparator" in source


def test_comparator_charts_do_not_require_webgl() -> None:
    index = pd.date_range("2024-01-01", periods=1_500, freq="D")
    normalized = pd.DataFrame({"SPY": range(100, 1_600), "QQQ": range(200, 1_700)}, index=index)
    returns = normalized.pct_change(fill_method=None).dropna()
    rolling = returns["SPY"].rolling(60).corr(returns["QQQ"]).dropna()
    comparison = ComparisonData(normalized, returns, rolling, 1.0)

    figures = _comparison_figures(comparison, "SPY", "QQQ", 60)

    assert all(trace.type == "scatter" for figure in figures for trace in figure.data)
