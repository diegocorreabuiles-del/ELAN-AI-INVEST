from __future__ import annotations

import math
from typing import cast

import numpy as np

from .models import FundamentalAnalysis, FundamentalSnapshot


def _present(value: float | None) -> bool:
    return value is not None and not (isinstance(value, float) and math.isnan(value))


def _numeric(value: float | None) -> float | None:
    if not _present(value):
        return None
    assert value is not None
    return float(value)


def _percent(value: float | None) -> float | None:
    numeric = _numeric(value)
    if numeric is None:
        return None
    return numeric * 100 if abs(numeric) <= 2 else numeric


def _bounded(value: float) -> float:
    return float(np.clip(value, 0, 100))


def _quality(snapshot: FundamentalSnapshot) -> float:
    points: list[float] = []
    roe = _percent(snapshot.return_on_equity)
    roa = _percent(snapshot.return_on_assets)
    margin = _percent(snapshot.profit_margin)
    operating = _percent(snapshot.operating_margin)
    if roe is not None:
        points.append(_bounded(40 + roe * 2.0))
    if roa is not None:
        points.append(_bounded(45 + roa * 3.0))
    if margin is not None:
        points.append(_bounded(45 + margin * 2.0))
    if operating is not None:
        points.append(_bounded(45 + operating * 1.8))
    return float(np.mean(points)) if points else 50.0


def _growth(snapshot: FundamentalSnapshot) -> float:
    points: list[float] = []
    revenue = _percent(snapshot.revenue_growth)
    earnings = _percent(snapshot.earnings_growth)
    if revenue is not None:
        points.append(_bounded(50 + revenue * 2.0))
    if earnings is not None:
        points.append(_bounded(50 + earnings * 1.5))
    return float(np.mean(points)) if points else 50.0


def _valuation(snapshot: FundamentalSnapshot) -> float:
    points: list[float] = []
    for value, optimum, penalty in (
        (snapshot.forward_pe, 18.0, 2.0),
        (snapshot.trailing_pe, 20.0, 1.7),
        (snapshot.enterprise_to_ebitda, 12.0, 2.8),
        (snapshot.price_to_book, 3.0, 7.0),
    ):
        numeric = _numeric(value)
        if numeric is not None and numeric > 0:
            points.append(_bounded(78 - abs(numeric - optimum) * penalty))
    peg_ratio = _numeric(snapshot.peg_ratio)
    if peg_ratio is not None and peg_ratio > 0:
        points.append(_bounded(85 - abs(peg_ratio - 1.3) * 30))
    return float(np.mean(points)) if points else 50.0


def _balance_sheet(snapshot: FundamentalSnapshot) -> float:
    points: list[float] = []
    debt = _numeric(snapshot.debt_to_equity)
    if debt is not None:
        if debt > 10:
            debt /= 100
        points.append(_bounded(90 - debt * 35))
    ratio = _numeric(snapshot.current_ratio)
    if ratio is not None:
        points.append(_bounded(45 + min(ratio, 3.0) * 20))
    return float(np.mean(points)) if points else 50.0


def _cash_flow(snapshot: FundamentalSnapshot) -> float:
    points: list[float] = []
    free_cash_flow = _numeric(snapshot.free_cash_flow)
    operating_cash_flow = _numeric(snapshot.operating_cash_flow)
    if free_cash_flow is not None:
        points.append(85.0 if free_cash_flow > 0 else 20.0)
    if operating_cash_flow is not None:
        points.append(85.0 if operating_cash_flow > 0 else 20.0)
    if free_cash_flow is not None and operating_cash_flow is not None:
        operating = abs(operating_cash_flow)
        if operating > 0:
            conversion = free_cash_flow / operating
            points.append(_bounded(45 + conversion * 50))
    return float(np.mean(points)) if points else 50.0


def analyze_fundamentals(snapshot: FundamentalSnapshot) -> FundamentalAnalysis:
    quality = _quality(snapshot)
    growth = _growth(snapshot)
    valuation = _valuation(snapshot)
    balance = _balance_sheet(snapshot)
    cash_flow = _cash_flow(snapshot)
    score = _bounded(
        quality * 0.28 + growth * 0.22 + valuation * 0.22 + balance * 0.14 + cash_flow * 0.14
    )

    values = list(snapshot.as_dict().values())[4:]
    available = sum(_present(cast(float | None, value)) for value in values)
    confidence = _bounded(35 + available / max(len(values), 1) * 65)

    if score >= 75:
        decision = "CALIDAD ALTA"
    elif score >= 60:
        decision = "FAVORABLE"
    elif score >= 45:
        decision = "NEUTRAL"
    else:
        decision = "DÉBIL"

    strengths: list[str] = []
    risks: list[str] = []
    if quality >= 65:
        strengths.append("rentabilidad y márgenes sólidos")
    if growth >= 65:
        strengths.append("crecimiento superior")
    if valuation >= 65:
        strengths.append("valoración razonable")
    if balance >= 65:
        strengths.append("balance financiero controlado")
    if cash_flow >= 65:
        strengths.append("buena generación de caja")
    if valuation < 40:
        risks.append("valoración exigente")
    if balance < 40:
        risks.append("apalancamiento o liquidez débiles")
    if growth < 40:
        risks.append("crecimiento insuficiente")

    explanation = (
        "Fortalezas: " + (", ".join(strengths) if strengths else "sin ventaja clara") + "."
    )
    if risks:
        explanation += " Riesgos: " + ", ".join(risks) + "."

    return FundamentalAnalysis(
        symbol=snapshot.symbol,
        score=round(score, 1),
        quality_score=round(quality, 1),
        growth_score=round(growth, 1),
        valuation_score=round(valuation, 1),
        balance_sheet_score=round(balance, 1),
        cash_flow_score=round(cash_flow, 1),
        confidence=round(confidence, 1),
        decision=decision,
        explanation=explanation,
        snapshot=snapshot,
    )
