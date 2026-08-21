from __future__ import annotations

import math
from collections.abc import Mapping

import pandas as pd
import streamlit as st

from elan_ai_invest.analysis import AssetAnalysis, AssetProfile, AssetType, build_asset_analysis
from elan_ai_invest.core.config import MarketConfig
from elan_ai_invest.providers.base import MarketDataAssetQuality

from . import market as market_dashboard


def load_decision_analysis(
    profile: AssetProfile,
    *,
    period: str,
    market_config: MarketConfig,
    quality: MarketDataAssetQuality | None,
    benchmark_history: pd.DataFrame | pd.Series | None,
    market_regime: str,
    annualisation_days: int,
    error_count: int,
) -> AssetAnalysis:
    history = market_dashboard._load_history(
        profile.symbol,
        period,
        market_config.timeout_seconds,
        market_config.max_retries,
        market_config.backoff_seconds,
    )
    return build_asset_analysis(
        profile,
        history,
        quality=quality,
        benchmark_history=benchmark_history,
        market_regime=market_regime,
        annualisation_days=annualisation_days,
        error_count=error_count,
    )


def _number(value: float | None, *, suffix: str = "", decimals: int = 1) -> str:
    if value is None or not math.isfinite(value):
        return "N/D"
    return f"{value:,.{decimals}f}{suffix}"


def _price(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "N/D"
    decimals = 6 if abs(value) < 1 else 2
    return f"{value:,.{decimals}f}"


def _compact(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "N/D"
    absolute = abs(value)
    for divisor, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if absolute >= divisor:
            return f"{value / divisor:,.2f}{suffix}"
    return f"{value:,.2f}"


def _trend(score: float | None) -> str:
    if score is None:
        return "N/D"
    if score >= 65:
        return "Alcista"
    if score <= 35:
        return "Bajista"
    return "Neutral"


def _ranking_row(ranking: pd.DataFrame, symbol: str) -> pd.Series | None:
    matches = ranking.loc[ranking["symbol"].eq(symbol)]
    return None if matches.empty else matches.iloc[0]


def _render_selected_asset(
    analysis: AssetAnalysis | None,
    ranking: pd.DataFrame,
    active_symbol: str,
    labels: Mapping[str, str],
) -> None:
    row = _ranking_row(ranking, active_symbol)
    profile = analysis.profile if analysis is not None else None
    technical = analysis.technical if analysis is not None else None
    market = analysis.market if analysis is not None else None
    signal = "N/D" if row is None else str(row.get("signal", row.get("decision", "N/D")))
    score_value = None if row is None else row.get("score")
    if analysis is not None and analysis.profile.asset_type is AssetType.STABLECOIN:
        signal = analysis.decision.value
        score_value = analysis.scores.conviction
    name = profile.name if profile is not None else labels.get(active_symbol, active_symbol)

    with st.container(horizontal=True, gap="xsmall"):
        st.metric("Activo", f"{active_symbol} · {name}", border=True)
        st.metric("Precio", _price(market.price if market else None), border=True)
        st.metric(
            "Variación 1D",
            _number(market.change_1d_pct if market else None, suffix="%", decimals=2),
            border=True,
        )
        st.metric("Score activo", _number(score_value, suffix="/100"), border=True)
        st.metric("Señal", signal or "N/D", border=True)
        if analysis is not None and analysis.profile.asset_type is AssetType.STABLECOIN:
            stablecoin = analysis.stablecoin
            st.metric(
                "Peg health",
                _number(
                    stablecoin.peg_health_score if stablecoin else None,
                    suffix="/100",
                ),
                border=True,
            )
            st.metric(
                "Riesgo de depeg",
                stablecoin.depeg_risk.value if stablecoin else "N/D",
                border=True,
            )
        else:
            st.metric(
                "Tendencia", _trend(technical.trend_score if technical else None), border=True
            )
            st.metric(
                "Momentum",
                "N/D" if technical is None else f"RSI {_number(technical.rsi_14, decimals=0)}",
                border=True,
            )


def _render_technical_details(analysis: AssetAnalysis) -> None:
    technical = analysis.technical
    if technical is None:
        return
    with st.expander("Desglose técnico"):
        with st.container(horizontal=True, gap="xsmall"):
            st.metric("Tendencia", _number(technical.trend_score, suffix="/100"), border=True)
            st.metric("Momentum", _number(technical.momentum_score, suffix="/100"), border=True)
            st.metric("Volumen", _number(technical.volume_score, suffix="/100"), border=True)
            st.metric(
                "Volatilidad",
                _number(technical.volatility_score, suffix="/100"),
                border=True,
            )
            st.metric("Estructura", _number(technical.structure_score, suffix="/100"), border=True)
        st.caption(
            " · ".join(
                (
                    f"Precio vs SMA50: {_number(technical.price_vs_sma_50_pct, suffix='%', decimals=2)}",
                    f"Precio vs SMA200: {_number(technical.price_vs_sma_200_pct, suffix='%', decimals=2)}",
                    f"MACD: {_number(technical.macd, decimals=3)}",
                    f"ADX: {_number(technical.adx_14)}",
                    f"ATR: {_number(technical.atr_14, decimals=3)}",
                    f"RVOL: {_number(technical.rvol_20, suffix='x', decimals=2)}",
                )
            )
        )


def _render_decision(analysis: AssetAnalysis | None) -> None:
    with st.container(border=True):
        st.subheader("Decisión", anchor=False)
        if analysis is None:
            st.info("Decisión no disponible: no se pudo completar el histórico del activo.")
            return
        scores = analysis.scores
        confidence = analysis.data_confidence
        with st.container(horizontal=True, gap="xsmall"):
            st.metric("Convicción", _number(scores.conviction, suffix="/100"), border=True)
            st.metric("Decisión", analysis.decision.value, border=True)
            st.metric(
                "Confianza datos",
                _number(confidence.score if confidence else None, suffix="%"),
                border=True,
            )
        with st.container(horizontal=True, gap="xsmall"):
            if analysis.profile.asset_type is AssetType.STABLECOIN:
                st.metric("Peg health", _number(scores.peg_health, suffix="/100"), border=True)
                st.metric("Liquidez", _number(scores.liquidity, suffix="/100"), border=True)
                st.metric("Riesgo emisor", _number(scores.issuer_risk, suffix="/100"), border=True)
                st.metric("Adopción", _number(scores.adoption, suffix="/100"), border=True)
            elif analysis.profile.is_crypto_asset:
                st.metric("Técnico", _number(scores.technical, suffix="/100"), border=True)
                st.metric("Sentimiento", _number(scores.sentiment, suffix="/100"), border=True)
                st.metric(
                    "Institucional", _number(scores.institutional, suffix="/100"), border=True
                )
                st.metric("Riesgo", _number(scores.risk, suffix="/100"), border=True)
            else:
                st.metric("Técnico", _number(scores.technical, suffix="/100"), border=True)
                st.metric("Fundamental", _number(scores.fundamental, suffix="/100"), border=True)
                st.metric("Sentimiento", _number(scores.sentiment, suffix="/100"), border=True)
                st.metric(
                    "Institucional", _number(scores.institutional, suffix="/100"), border=True
                )
                st.metric("Riesgo", _number(scores.risk, suffix="/100"), border=True)
        if analysis.decision_reasons:
            st.caption(" · ".join(analysis.decision_reasons))
        if confidence is not None and confidence.warnings:
            st.warning(" ".join(confidence.warnings))
        if analysis.profile.asset_type is not AssetType.STABLECOIN:
            _render_technical_details(analysis)


def _render_trade_plan(analysis: AssetAnalysis | None) -> None:
    with st.container(border=True):
        st.subheader("Plan de operación", anchor=False)
        plan = analysis.trade_plan if analysis is not None else None
        if analysis is not None and analysis.profile.asset_type is AssetType.STABLECOIN:
            st.info("Plan direccional tradicional: no aplica a stablecoins.")
            return
        if plan is None or not plan.sufficient_data:
            reason = (
                plan.rationale[0]
                if plan is not None and plan.rationale
                else "Histórico no disponible."
            )
            st.info(f"Plan de operación: datos insuficientes. {reason}")
            return
        assert analysis is not None
        with st.container(horizontal=True, gap="xsmall"):
            st.metric("Precio actual", _price(analysis.market.price), border=True)
            st.metric(
                "Zona de entrada",
                f"{_price(plan.entry_low)} – {_price(plan.entry_high)}",
                border=True,
            )
            st.metric("Stop técnico", _price(plan.stop), border=True)
            st.metric("Target 1", _price(plan.target_1), border=True)
            st.metric("Target 2", _price(plan.target_2), border=True)
            st.metric("R/R T1", _number(plan.risk_reward_1, suffix="x", decimals=2), border=True)
            st.metric("R/R T2", _number(plan.risk_reward_2, suffix="x", decimals=2), border=True)
        st.caption(" ".join(plan.rationale))


def _render_asset_specific(analysis: AssetAnalysis | None) -> None:
    if analysis is None or not analysis.profile.is_crypto_asset:
        return
    if analysis.profile.asset_type is AssetType.CRYPTO:
        crypto_metrics = analysis.crypto
        with st.container(border=True):
            st.subheader("Contexto crypto", anchor=False)
            with st.container(horizontal=True, gap="xsmall"):
                st.metric(
                    "Fuerza vs BTC · 30D",
                    _number(
                        crypto_metrics.btc_relative_strength_30d_pct if crypto_metrics else None,
                        suffix=" pp",
                        decimals=2,
                    ),
                    border=True,
                )
                st.metric(
                    "Actividad volumen · 20D",
                    _number(
                        crypto_metrics.volume_change_20d_pct if crypto_metrics else None,
                        suffix="%",
                        decimals=1,
                    ),
                    border=True,
                )
                st.metric(
                    "Volumen monetario medio",
                    _compact(crypto_metrics.average_dollar_volume if crypto_metrics else None),
                    border=True,
                )
                st.metric(
                    "RVOL 20",
                    _number(
                        analysis.technical.rvol_20 if analysis.technical else None,
                        suffix="x",
                        decimals=2,
                    ),
                    border=True,
                )
            st.caption(
                "Derivados — Funding: N/D · Open interest: N/D · Liquidaciones: N/D · "
                "Long/Short: N/D"
            )
            st.caption(
                "On-chain y red — MVRV: N/D · SOPR: N/D · Netflow: N/D · "
                "Direcciones activas: N/D · TVL/fees: N/D"
            )
    elif analysis.profile.asset_type is AssetType.MEME_COIN:
        meme_metrics = analysis.meme_coin
        with st.container(border=True):
            st.subheader("Perfil meme coin", anchor=False)
            st.warning(
                "Activo altamente especulativo: momentum, volumen y liquidez pueden cambiar "
                "de forma abrupta."
            )
            with st.container(horizontal=True, gap="xsmall"):
                st.metric(
                    "Momentum",
                    _number(meme_metrics.momentum_score if meme_metrics else None, suffix="/100"),
                    border=True,
                )
                st.metric(
                    "Volumen",
                    _number(meme_metrics.volume_score if meme_metrics else None, suffix="/100"),
                    border=True,
                )
                st.metric(
                    "RVOL 20",
                    _number(meme_metrics.rvol_20 if meme_metrics else None, suffix="x", decimals=2),
                    border=True,
                )
                st.metric(
                    "Actividad volumen · 20D",
                    _number(
                        meme_metrics.volume_change_20d_pct if meme_metrics else None,
                        suffix="%",
                        decimals=1,
                    ),
                    border=True,
                )
                st.metric(
                    "Volumen monetario medio",
                    _compact(meme_metrics.average_dollar_volume if meme_metrics else None),
                    border=True,
                )
            st.caption(
                "DEX/holders/social — Liquidez DEX: N/D · Concentración holders: N/D · "
                "Whale flows: N/D · Social momentum: N/D"
            )
            st.caption("Derivados — Funding: N/D · Open interest: N/D · Liquidaciones: N/D")
    else:
        stablecoin_metrics = analysis.stablecoin
        with st.container(border=True):
            st.subheader("Salud de stablecoin", anchor=False)
            with st.container(horizontal=True, gap="xsmall"):
                st.metric(
                    "Peg health",
                    _number(
                        stablecoin_metrics.peg_health_score if stablecoin_metrics else None,
                        suffix="/100",
                    ),
                    border=True,
                )
                st.metric(
                    "Desviación peg",
                    _number(
                        stablecoin_metrics.peg_deviation_pct if stablecoin_metrics else None,
                        suffix="%",
                        decimals=3,
                    ),
                    border=True,
                )
                st.metric(
                    "Desviación máxima · 30 sesiones",
                    _number(
                        (
                            stablecoin_metrics.max_peg_deviation_30d_pct
                            if stablecoin_metrics
                            else None
                        ),
                        suffix="%",
                        decimals=3,
                    ),
                    border=True,
                )
                st.metric(
                    "Riesgo de depeg",
                    stablecoin_metrics.depeg_risk.value if stablecoin_metrics else "N/D",
                    border=True,
                )
                st.metric(
                    "Actividad volumen · 20D",
                    _number(
                        stablecoin_metrics.volume_change_20d_pct if stablecoin_metrics else None,
                        suffix="%",
                        decimals=1,
                    ),
                    border=True,
                )
            if stablecoin_metrics is not None and stablecoin_metrics.depeg_risk.value in {
                "ALTO",
                "CRÍTICO",
            }:
                st.warning("El histórico observado muestra riesgo material de pérdida del peg.")
            st.caption(
                "Liquidez profunda/emisor — DEX: N/D · Exchanges: N/D · Reservas: N/D · "
                "Riesgo emisor: N/D"
            )
            st.caption(
                "Supply/adopción — Supply 7D/30D: N/D · Market cap: N/D · "
                "Distribución por cadenas: N/D"
            )


def _render_explanations(analysis: AssetAnalysis | None) -> None:
    if analysis is None or not (analysis.positives or analysis.negatives):
        return
    with st.container(horizontal=True, gap="small"):
        with st.container(border=True, width="stretch"):
            st.markdown("**Qué favorece la señal**")
            for reason in analysis.positives:
                st.markdown(f"- {reason}")
        with st.container(border=True, width="stretch"):
            st.markdown("**Qué perjudica la señal**")
            for reason in analysis.negatives:
                st.markdown(f"- {reason}")


def render_decision_terminal(
    analysis: AssetAnalysis | None,
    ranking: pd.DataFrame,
    active_symbol: str,
    labels: Mapping[str, str],
) -> None:
    _render_selected_asset(analysis, ranking, active_symbol, labels)
    _render_decision(analysis)
    _render_trade_plan(analysis)
    _render_asset_specific(analysis)
    _render_explanations(analysis)
