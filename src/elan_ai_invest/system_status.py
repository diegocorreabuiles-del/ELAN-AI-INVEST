from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from elan_ai_invest import __version__
from elan_ai_invest.core.config import Settings


@dataclass(frozen=True)
class SystemStatus:
    version: str
    python_version: str
    operating_system: str
    environment: str
    market_provider: str
    checks: dict[str, bool]

    @property
    def ok(self) -> bool:
        return all(self.checks.values())

    def as_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"comprobación": name, "estado": "OK" if passed else "PENDIENTE"}
                for name, passed in self.checks.items()
            ]
        )


def collect_system_status(root: Path, settings: Settings) -> SystemStatus:
    checks = {
        "Configuración": (root / "config" / "settings.yaml").exists(),
        "Watchlist": (root / "config" / "watchlist.csv").exists(),
        "Carpeta de datos": (root / "data").exists(),
        "Carpeta de logs": (root / "logs").exists(),
        "Base histórica accesible": (root / settings.storage.database_path).parent.exists(),
        "Base paper trading accesible": (
            root / settings.paper_trading.database_path
        ).parent.exists(),
    }
    return SystemStatus(
        version=__version__,
        python_version=".".join(map(str, sys.version_info[:3])),
        operating_system=platform.platform(),
        environment=settings.app.environment,
        market_provider=settings.market.provider,
        checks=checks,
    )
