from __future__ import annotations

from elan_ai_invest.providers.base import MarketDataAssetQuality, MarketDataQualityStatus

from .models import DataConfidence

_STATUS_WARNING = {
    MarketDataQualityStatus.DEGRADED: "Cobertura de mercado degradada.",
    MarketDataQualityStatus.STALE: "Los datos de mercado están desactualizados.",
    MarketDataQualityStatus.INSUFFICIENT: "El histórico disponible es insuficiente.",
    MarketDataQualityStatus.UNAVAILABLE: "Los datos de mercado no están disponibles.",
}
_STATUS_SCORE_CAP = {
    MarketDataQualityStatus.DEGRADED: 75.0,
    MarketDataQualityStatus.STALE: 50.0,
    MarketDataQualityStatus.INSUFFICIENT: 40.0,
    MarketDataQualityStatus.UNAVAILABLE: 0.0,
}


def _bounded(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def calculate_data_confidence(
    quality: MarketDataAssetQuality | None,
    *,
    available_fields: int | None = None,
    expected_fields: int | None = None,
    provider_score: float | None = None,
    error_count: int = 0,
    warning_threshold: float = 70.0,
) -> DataConfidence:
    """Score observable data quality; absent evidence produces zero confidence."""

    if error_count < 0:
        raise ValueError("error_count no puede ser negativo")
    if (available_fields is None) is not (expected_fields is None):
        raise ValueError("available_fields y expected_fields deben informarse juntos")
    if expected_fields is not None and expected_fields <= 0:
        raise ValueError("expected_fields debe ser mayor que cero")
    if available_fields is not None:
        assert expected_fields is not None
        if not 0 <= available_fields <= expected_fields:
            raise ValueError("available_fields debe estar entre cero y expected_fields")
    if provider_score is not None and not 0 <= provider_score <= 100:
        raise ValueError("provider_score debe estar entre 0 y 100")

    coverage = _bounded(quality.coverage_ratio * 100) if quality is not None else None
    freshness = None
    if quality is not None and quality.age_days is not None:
        freshness = _bounded(100 - max(0, quality.age_days - 1) * 20)
    fields = None
    if available_fields is not None and expected_fields is not None:
        fields = _bounded(available_fields / expected_fields * 100)

    weighted = ((coverage, 0.40), (freshness, 0.30), (fields, 0.20), (provider_score, 0.10))
    available_weight = sum(weight for value, weight in weighted if value is not None)
    raw_score = (
        sum(float(value) * weight for value, weight in weighted if value is not None)
        / available_weight
        if available_weight
        else 0.0
    )
    score = _bounded(raw_score - min(error_count * 10.0, 40.0))
    if quality is not None and quality.status in _STATUS_SCORE_CAP:
        score = min(score, _STATUS_SCORE_CAP[quality.status])
    warnings: list[str] = []
    if quality is None:
        warnings.append("Sin evidencia de calidad del proveedor.")
    elif warning := _STATUS_WARNING.get(quality.status):
        warnings.append(warning)
    if fields is not None and fields < warning_threshold:
        warnings.append("Faltan campos relevantes para el análisis.")
    if error_count:
        warnings.append(f"Se registraron {error_count} errores de datos.")
    if score < warning_threshold:
        warnings.append("Convicción limitada por baja calidad de datos.")

    return DataConfidence(
        score=score,
        coverage_score=coverage,
        freshness_score=freshness,
        field_availability_score=fields,
        provider_score=provider_score,
        warnings=tuple(dict.fromkeys(warnings)),
    )
