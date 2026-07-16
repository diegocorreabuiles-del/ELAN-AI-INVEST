from __future__ import annotations

import importlib
from pathlib import Path

from elan_ai_invest.core.config import load_settings
from elan_ai_invest.system_status import collect_system_status


REQUIRED_MODULES = (
    "pandas",
    "numpy",
    "streamlit",
    "plotly",
    "yfinance",
    "yaml",
    "pydantic",
)


def _module_checks() -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for module in REQUIRED_MODULES:
        try:
            importlib.import_module(module)
            checks[f"Módulo {module}"] = True
        except Exception:
            checks[f"Módulo {module}"] = False
    return checks


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root / "config" / "settings.yaml")
    (root / "data").mkdir(exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)

    status = collect_system_status(root, settings)
    checks = dict(status.checks)
    checks.update(_module_checks())

    print(f"ELAN Quantum {status.version}")
    print(f"Python {status.python_version}")
    for name, passed in checks.items():
        print(f"[{'OK' if passed else 'ERROR'}] {name}")

    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
