from __future__ import annotations

import re
from pathlib import Path

from elan_ai_invest.dashboard.layout import safe_render as layout_safe_render
from elan_ai_invest.dashboard.safe import safe_render

ROOT = Path(__file__).resolve().parents[1]


def test_all_dashboard_tabs_are_lazy() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")

    assert 'on_change="rerun"' in source
    guarded_tabs = {int(index) for index in re.findall(r"if tabs\[(\d+)\]\.open:", source)}
    assert guarded_tabs == set(range(12))


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
