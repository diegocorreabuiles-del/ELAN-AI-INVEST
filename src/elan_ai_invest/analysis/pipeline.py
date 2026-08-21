from __future__ import annotations

import math

import pandas as pd

from elan_ai_invest.providers.base import MarketDataAssetQuality

from .crypto import (
    calculate_crypto_metrics,
    calculate_meme_coin_metrics,
    calculate_stablecoin_metrics,
)
from .data_confidence import calculate_data_confidence
from .decision import decide
from .models import (
    AssetAnalysis,
    AssetProfile,
    AssetType,
    CryptoMetrics,
    DepegRisk,
    RiskMetrics,
    StablecoinMetrics,
    TechnicalMetrics,
    TradePlan,
)
from .risk_engine import calculate_risk_metrics
from .score_engine import calculate_score_breakdown
from .technical import calculate_market_metrics, calculate_technical_metrics
from .trade_plan import calculate_trade_plan


def _present(values: tuple[float | None, ...]) -> int:
    return sum(value is not None and math.isfinite(value) for value in values)


def _explain(
    profile: AssetProfile,
    *,
    price: float | None,
    change_1d_pct: float | None,
    technical: TechnicalMetrics,
    risk: RiskMetrics,
    crypto: CryptoMetrics | None,
    stablecoin: StablecoinMetrics | None,
    confidence_warnings: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    positives: list[str] = []
    negatives: list[str] = []

    if stablecoin is not None:
        if stablecoin.depeg_risk is DepegRisk.LOW:
            positives.append("El precio mantiene el peg USD dentro del umbral observado.")
        elif stablecoin.depeg_risk is not DepegRisk.NOT_AVAILABLE:
            negatives.append(f"Riesgo de depeg {stablecoin.depeg_risk.value.lower()}.")
        negatives.extend(confidence_warnings)
        return tuple(dict.fromkeys(positives)), tuple(dict.fromkeys(negatives))

    if price is not None and technical.sma_200 is not None:
        if price > technical.sma_200:
            positives.append("Precio sobre SMA200.")
        else:
            negatives.append("Precio bajo SMA200.")
    if technical.rsi_14 is not None:
        if 45 <= technical.rsi_14 <= 70:
            positives.append("RSI en zona de momentum constructivo.")
        elif technical.rsi_14 > 70:
            negatives.append("RSI en zona de sobrecompra.")
        elif technical.rsi_14 < 30:
            negatives.append("RSI en zona de debilidad extrema.")
    if change_1d_pct is not None:
        if change_1d_pct > 0:
            positives.append("Sesión diaria positiva.")
        elif change_1d_pct < 0:
            negatives.append("Sesión diaria negativa.")
    if risk.score is not None:
        if risk.score >= 65:
            positives.append("Control de riesgo favorable en el histórico disponible.")
        elif risk.score < 45:
            negatives.append("Perfil de riesgo elevado en el histórico disponible.")
    if crypto is not None and crypto.btc_relative_strength_30d_pct is not None:
        if crypto.btc_relative_strength_30d_pct > 0:
            positives.append("Fuerza relativa 30D superior a BTC.")
        elif crypto.btc_relative_strength_30d_pct < 0:
            negatives.append("Fuerza relativa 30D inferior a BTC.")
    if profile.requires_speculative_warning:
        negatives.append("Activo especulativo: sensibilidad elevada a momentum y liquidez.")
    negatives.extend(confidence_warnings)
    return tuple(dict.fromkeys(positives)), tuple(dict.fromkeys(negatives))


def build_asset_analysis(
    profile: AssetProfile,
    history: pd.DataFrame,
    *,
    quality: MarketDataAssetQuality | None = None,
    benchmark_history: pd.DataFrame | pd.Series | None = None,
    market_regime: str | None = None,
    annualisation_days: int = 252,
    error_count: int = 0,
) -> AssetAnalysis:
    """Assemble one decision snapshot from observed data and deterministic engines."""

    market = calculate_market_metrics(history)
    technical = calculate_technical_metrics(history)
    risk = calculate_risk_metrics(
        history,
        benchmark_history,
        annualisation_days=annualisation_days,
    )
    crypto = (
        calculate_crypto_metrics(history, benchmark_history, market=market)
        if profile.asset_type is AssetType.CRYPTO
        else None
    )
    meme_coin = (
        calculate_meme_coin_metrics(history, market=market, technical=technical)
        if profile.asset_type is AssetType.MEME_COIN
        else None
    )
    stablecoin = (
        calculate_stablecoin_metrics(history, market=market)
        if profile.asset_type is AssetType.STABLECOIN
        else None
    )
    scores = calculate_score_breakdown(
        profile,
        technical=technical,
        risk=risk,
        stablecoin=stablecoin,
    )
    core_fields: tuple[float | None, ...] = (
        market.price,
        market.change_1d_pct,
        technical.score,
        technical.trend_score,
        technical.momentum_score,
        risk.score,
        risk.annual_volatility_pct,
        risk.var_95_daily_pct,
        risk.maximum_drawdown_pct,
        risk.atr_pct,
    )
    if crypto is not None:
        core_fields += (
            crypto.btc_relative_strength_30d_pct,
            crypto.volume_change_20d_pct,
            crypto.average_dollar_volume,
            crypto.funding_rate_pct,
            crypto.open_interest,
            crypto.exchange_netflow,
            crypto.mvrv,
        )
    elif meme_coin is not None:
        core_fields += (
            meme_coin.rvol_20,
            meme_coin.volume_change_20d_pct,
            meme_coin.average_dollar_volume,
            meme_coin.dex_liquidity,
            meme_coin.holder_growth_30d_pct,
            meme_coin.top_holders_concentration_pct,
            meme_coin.social_momentum_score,
        )
    elif stablecoin is not None:
        core_fields = (
            market.price,
            stablecoin.peg_health_score,
            stablecoin.peg_deviation_pct,
            stablecoin.max_peg_deviation_30d_pct,
            stablecoin.volume_change_20d_pct,
            stablecoin.average_dollar_volume,
            stablecoin.liquidity_health_score,
            stablecoin.issuer_risk_score,
            stablecoin.adoption_trend_score,
            stablecoin.supply_change_30d_pct,
        )
    data_confidence = calculate_data_confidence(
        quality,
        available_fields=_present(core_fields),
        expected_fields=len(core_fields),
        error_count=error_count,
    )
    decision_result = decide(
        scores.conviction,
        asset_type=profile.asset_type,
        data_confidence=data_confidence,
        risk_score=risk.score,
        trend_score=technical.trend_score,
        market_regime=market_regime,
    )
    trade_plan = (
        TradePlan(
            sufficient_data=False,
            rationale=("Una stablecoin no utiliza un plan direccional tradicional.",),
        )
        if profile.asset_type is AssetType.STABLECOIN
        else calculate_trade_plan(history)
    )
    positives, negatives = _explain(
        profile,
        price=market.price,
        change_1d_pct=market.change_1d_pct,
        technical=technical,
        risk=risk,
        crypto=crypto,
        stablecoin=stablecoin,
        confidence_warnings=data_confidence.warnings,
    )
    return AssetAnalysis(
        profile=profile,
        market=market,
        technical=technical,
        risk=risk,
        crypto=crypto,
        meme_coin=meme_coin,
        stablecoin=stablecoin,
        trade_plan=trade_plan,
        scores=scores,
        data_confidence=data_confidence,
        decision=decision_result.action,
        decision_reasons=decision_result.reasons,
        decision_limited_by_data_quality=decision_result.limited_by_data_quality,
        positives=positives,
        negatives=negatives,
    )
