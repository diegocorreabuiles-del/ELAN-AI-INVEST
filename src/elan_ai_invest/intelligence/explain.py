from .models import Decision


def build_explanation(decision: Decision) -> str:

    reasons = []

    if decision.score >= 85:
        reasons.append("Tendencia muy sólida.")
    elif decision.score >= 70:
        reasons.append("Tendencia positiva.")

    if decision.confidence >= 85:
        reasons.append("Alta confianza del modelo.")
    elif decision.confidence >= 70:
        reasons.append("Confianza moderada.")

    if decision.action.value == "BUY":
        reasons.append("Condiciones favorables para incorporar el activo.")

    elif decision.action.value == "HOLD":
        reasons.append("Se recomienda mantener la posición.")

    elif decision.action.value == "WAIT":
        reasons.append("Mejor esperar una señal más clara.")

    elif decision.action.value == "REDUCE":
        reasons.append("Conviene reducir exposición.")

    elif decision.action.value == "SELL":
        reasons.append("Riesgo elevado. Salida recomendada.")

    return " ".join(reasons)