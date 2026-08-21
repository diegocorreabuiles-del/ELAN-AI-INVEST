from __future__ import annotations

import math
from dataclasses import dataclass

from .models import AssetType, DataConfidence, DecisionAction, DecisionResult


@dataclass(frozen=True, slots=True)
class DecisionPolicy:
    buy_threshold: float = 80.0
    accumulate_threshold: float = 65.0
    wait_threshold: float = 45.0
    reduce_threshold: float = 30.0
    minimum_confidence: float = 40.0
    buy_confidence: float = 70.0
    accumulate_confidence: float = 55.0
    severe_risk_score: float = 30.0
    elevated_risk_score: float = 45.0
    weak_trend_score: float = 35.0

    def __post_init__(self) -> None:
        thresholds = (
            self.buy_threshold,
            self.accumulate_threshold,
            self.wait_threshold,
            self.reduce_threshold,
        )
        if not all(math.isfinite(value) and 0 <= value <= 100 for value in thresholds):
            raise ValueError("Los umbrales de decisión deben estar entre 0 y 100")
        if not all(left > right for left, right in zip(thresholds, thresholds[1:], strict=False)):
            raise ValueError("Los umbrales de decisión deben estar estrictamente ordenados")
        if not self.minimum_confidence <= self.accumulate_confidence <= self.buy_confidence:
            raise ValueError("Los umbrales de confianza deben estar ordenados")
        if self.severe_risk_score > self.elevated_risk_score:
            raise ValueError("Los umbrales de riesgo deben estar ordenados")


DEFAULT_DECISION_POLICY = DecisionPolicy()


def _base_action(score: float, policy: DecisionPolicy) -> DecisionAction:
    if score >= policy.buy_threshold:
        return DecisionAction.BUY
    if score >= policy.accumulate_threshold:
        return DecisionAction.ACCUMULATE
    if score >= policy.wait_threshold:
        return DecisionAction.WAIT
    if score >= policy.reduce_threshold:
        return DecisionAction.REDUCE
    return DecisionAction.SELL


def decide(
    conviction: float | None,
    *,
    asset_type: AssetType,
    data_confidence: DataConfidence | None,
    risk_score: float | None = None,
    trend_score: float | None = None,
    market_regime: str | None = None,
    policy: DecisionPolicy = DEFAULT_DECISION_POLICY,
) -> DecisionResult:
    """Apply deterministic, conservative gates to the conviction score."""

    for name, value in (
        ("conviction", conviction),
        ("risk_score", risk_score),
        ("trend_score", trend_score),
    ):
        if value is not None and (not math.isfinite(value) or not 0 <= value <= 100):
            raise ValueError(f"{name} debe estar entre 0 y 100")
    if conviction is None or data_confidence is None:
        return DecisionResult(
            action=DecisionAction.NOT_AVAILABLE,
            base_action=DecisionAction.NOT_AVAILABLE,
            limited_by_data_quality=True,
            reasons=("No hay datos suficientes para emitir una decisión.",),
        )

    base = _base_action(conviction, policy)
    action = base
    reasons: list[str] = []
    limited = False

    if asset_type is AssetType.STABLECOIN:
        action = DecisionAction.WAIT
        reasons.append("Una stablecoin se evalúa por estabilidad y riesgo, no por revalorización.")
    if data_confidence.score < policy.minimum_confidence:
        action = DecisionAction.WAIT
        limited = True
        reasons.append("La calidad de datos no permite una recomendación direccional.")
    elif action is DecisionAction.BUY and data_confidence.score < policy.buy_confidence:
        action = DecisionAction.ACCUMULATE
        limited = True
        reasons.append("La confianza de datos no alcanza el umbral de compra.")
    if action is DecisionAction.ACCUMULATE and data_confidence.score < policy.accumulate_confidence:
        action = DecisionAction.WAIT
        limited = True
        reasons.append("La confianza de datos no alcanza el umbral de acumulación.")

    if risk_score is not None and risk_score < policy.severe_risk_score:
        if action in {DecisionAction.BUY, DecisionAction.ACCUMULATE}:
            action = DecisionAction.WAIT
            reasons.append("El riesgo severo bloquea una recomendación alcista.")
    elif risk_score is not None and risk_score < policy.elevated_risk_score:
        if action is DecisionAction.BUY:
            action = DecisionAction.ACCUMULATE
            reasons.append("El riesgo elevado reduce la intensidad de la recomendación.")

    if trend_score is not None and trend_score < policy.weak_trend_score:
        if action in {DecisionAction.BUY, DecisionAction.ACCUMULATE}:
            action = DecisionAction.WAIT
            reasons.append("La tendencia débil no confirma una recomendación alcista.")

    normalized_regime = (market_regime or "").strip().casefold().replace("-", "_").replace(" ", "_")
    if normalized_regime in {"risk_off", "defensivo"} and action is DecisionAction.BUY:
        action = DecisionAction.ACCUMULATE
        reasons.append("El régimen defensivo reduce la intensidad de la recomendación.")
    if asset_type is AssetType.MEME_COIN and action is DecisionAction.BUY:
        action = DecisionAction.ACCUMULATE
        reasons.append("El perfil especulativo limita la recomendación máxima.")
    if asset_type is AssetType.UNKNOWN and action in {
        DecisionAction.BUY,
        DecisionAction.ACCUMULATE,
    }:
        action = DecisionAction.WAIT
        reasons.append("El tipo de activo debe confirmarse antes de una recomendación alcista.")

    return DecisionResult(
        action=action,
        base_action=base,
        limited_by_data_quality=limited,
        reasons=tuple(reasons),
    )
