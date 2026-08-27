from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_module_lifecycle_is_complete_and_matches_app_reachability() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "check_module_lifecycle.py"),
            "--root",
            str(ROOT),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)

    assert report["total"] == 118
    assert report["active"] == 86
    assert report["compatibility"] == 13
    assert report["legacy"] == 19
    assert "elan_ai_invest.core.pipeline" in report["compatibility_modules"]
    assert "elan_ai_invest.legacy.pipeline_v1" in report["legacy_modules"]
