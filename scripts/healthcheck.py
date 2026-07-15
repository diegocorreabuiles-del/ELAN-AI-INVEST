from __future__ import annotations

from pathlib import Path

from elan_ai_invest.core.config import load_settings
from elan_ai_invest.system_status import collect_system_status


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root / "config" / "settings.yaml")
    (root / "data").mkdir(exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    status = collect_system_status(root, settings)
    print(f"ELAN Quantum {status.version}")
    print(f"Python {status.python_version}")
    for name, passed in status.checks.items():
        print(f"[{'OK' if passed else 'ERROR'}] {name}")
    return 0 if status.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
