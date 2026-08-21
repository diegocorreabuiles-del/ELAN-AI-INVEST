from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from .models import FxHistory


@dataclass(frozen=True)
class FxQualityIncident:
    code: str
    message: str
    severity: str


@dataclass(frozen=True)
class FxQualityReport:
    status: str
    score: float
    observations: int
    coverage_ratio: float
    last_updated: pd.Timestamp | None
    incidents: tuple[FxQualityIncident, ...]


def assess_fx_quality(
    history: FxHistory,
    *,
    now: datetime | pd.Timestamp | None = None,
    max_staleness_days: int = 5,
    max_abs_log_return: float = 0.35,
) -> FxQualityReport:
    incidents: list[FxQualityIncident] = []
    close = pd.to_numeric(history.prices.get("Close"), errors="coerce")
    invalid = (~np.isfinite(close)) | close.le(0)
    if invalid.any():
        incidents.append(
            FxQualityIncident("INVALID_RATE", "Hay cotizaciones no positivas o no finitas.", "high")
        )
    valid_close = close.where(~invalid).dropna()
    jumps = np.log(valid_close / valid_close.shift(1)).abs().dropna()
    if jumps.gt(max_abs_log_return).any():
        incidents.append(
            FxQualityIncident(
                "EXTREME_JUMP",
                "Se detectó al menos un salto diario superior al umbral configurado.",
                "medium",
            )
        )
    generated_at = pd.Timestamp(now if now is not None else datetime.now(UTC))
    generated_at = (
        generated_at.tz_localize("UTC")
        if generated_at.tzinfo is None
        else generated_at.tz_convert("UTC")
    )
    last_updated = history.market_timestamp
    last_updated = (
        last_updated.tz_localize("UTC")
        if last_updated.tzinfo is None
        else last_updated.tz_convert("UTC")
    )
    age_days = max((generated_at.normalize() - last_updated.normalize()).days, 0)
    if age_days > max_staleness_days:
        incidents.append(
            FxQualityIncident(
                "STALE", f"El último cierre tiene {age_days} días de antigüedad.", "medium"
            )
        )
    if history.coverage_ratio < 0.95:
        incidents.append(
            FxQualityIncident(
                "LOW_COVERAGE",
                f"La cobertura temporal es {history.coverage_ratio:.1%}.",
                "medium",
            )
        )
    penalty = sum(30 if item.severity == "high" else 15 for item in incidents)
    score = float(max(0, 100 - penalty))
    status = (
        "Saludable"
        if not incidents
        else "Crítica" if any(item.severity == "high" for item in incidents) else "Degradada"
    )
    return FxQualityReport(
        status=status,
        score=score,
        observations=history.observations,
        coverage_ratio=history.coverage_ratio,
        last_updated=last_updated,
        incidents=tuple(incidents),
    )


def validate_inverse_consistency(
    direct_rate: float,
    inverse_rate: float,
    *,
    tolerance: float = 0.005,
) -> FxQualityIncident | None:
    values = (float(direct_rate), float(inverse_rate))
    if any(not np.isfinite(value) or value <= 0 for value in values):
        return FxQualityIncident(
            "INVALID_INVERSE", "Las cotizaciones inversas no son válidas.", "high"
        )
    deviation = abs(values[0] * values[1] - 1.0)
    if deviation <= tolerance:
        return None
    return FxQualityIncident(
        "INVERSE_MISMATCH",
        f"El producto del par y su inverso se desvía {deviation:.2%} de 1.",
        "high",
    )


def validate_triangular_consistency(
    direct_rate: float,
    synthetic_rate: float,
    *,
    tolerance: float = 0.01,
) -> FxQualityIncident | None:
    values = (float(direct_rate), float(synthetic_rate))
    if any(not np.isfinite(value) or value <= 0 for value in values):
        return FxQualityIncident(
            "INVALID_TRIANGLE", "La comparación triangular no es válida.", "high"
        )
    deviation = abs(values[0] / values[1] - 1.0)
    if deviation <= tolerance:
        return None
    return FxQualityIncident(
        "TRIANGULAR_DEVIATION",
        f"El directo se desvía {deviation:.2%} del cruce sintético.",
        "high",
    )
