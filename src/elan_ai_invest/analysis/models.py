from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class AssetType(StrEnum):
    EQUITY = "equity"
    ETF = "etf"
    CRYPTO = "crypto"
    MEME_COIN = "meme_coin"
    STABLECOIN = "stablecoin"
    FOREX = "forex"
    BOND = "bond"
    COMMODITY = "commodity"
    INDEX = "index"
    FUND = "fund"
    UNKNOWN = "unknown"


class DecisionAction(StrEnum):
    BUY = "COMPRAR"
    ACCUMULATE = "ACUMULAR"
    WAIT = "ESPERAR"
    REDUCE = "REDUCIR"
    SELL = "VENDER"
    NOT_AVAILABLE = "N/D"


class DepegRisk(StrEnum):
    LOW = "BAJO"
    MODERATE = "MODERADO"
    HIGH = "ALTO"
    CRITICAL = "CRÍTICO"
    NOT_AVAILABLE = "N/D"


def _validate_score(name: str, value: float | None) -> None:
    if value is None:
        return
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError(f"{name} debe estar entre 0 y 100")


def _validate_finite(name: str, value: float | int | None) -> None:
    if value is not None and not math.isfinite(value):
        raise ValueError(f"{name} debe ser finito")


@dataclass(frozen=True, slots=True)
class AssetProfile:
    symbol: str
    name: str
    asset_type: AssetType
    catalog_asset_type: str | None = None
    country: str | None = None
    exchange: str | None = None
    benchmark: str | None = None
    classification_source: str = "catalog"
    classification_confidence: float = 100.0

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("El símbolo del activo no puede estar vacío")
        _validate_score("classification_confidence", self.classification_confidence)

    @property
    def supports_corporate_fundamentals(self) -> bool:
        return self.asset_type is AssetType.EQUITY

    @property
    def is_crypto_asset(self) -> bool:
        return self.asset_type in {
            AssetType.CRYPTO,
            AssetType.MEME_COIN,
            AssetType.STABLECOIN,
        }

    @property
    def requires_speculative_warning(self) -> bool:
        return self.asset_type is AssetType.MEME_COIN


@dataclass(frozen=True, slots=True)
class MarketMetrics:
    price: float | None = None
    change_1d_pct: float | None = None
    change_7d_pct: float | None = None
    change_30d_pct: float | None = None
    change_ytd_pct: float | None = None
    change_1y_pct: float | None = None
    volume: float | None = None
    average_volume_20d: float | None = None
    average_dollar_volume: float | None = None
    market_cap: float | None = None


@dataclass(frozen=True, slots=True)
class TechnicalMetrics:
    score: float | None = None
    trend_score: float | None = None
    momentum_score: float | None = None
    volume_score: float | None = None
    volatility_score: float | None = None
    structure_score: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    ema_20: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    adx_14: float | None = None
    atr_14: float | None = None
    rvol_20: float | None = None
    distance_to_high_52w_pct: float | None = None
    distance_to_low_52w_pct: float | None = None
    support: float | None = None
    resistance: float | None = None
    price_vs_sma_50_pct: float | None = None
    price_vs_sma_200_pct: float | None = None

    def __post_init__(self) -> None:
        for name in (
            "score",
            "trend_score",
            "momentum_score",
            "volume_score",
            "volatility_score",
            "structure_score",
        ):
            _validate_score(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class FundamentalMetrics:
    score: float | None = None
    valuation_score: float | None = None
    growth_score: float | None = None
    profitability_score: float | None = None
    balance_sheet_score: float | None = None
    cash_flow_score: float | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    peg: float | None = None
    price_to_sales: float | None = None
    enterprise_value_to_ebitda: float | None = None
    revenue_growth_pct: float | None = None
    earnings_growth_pct: float | None = None
    gross_margin_pct: float | None = None
    operating_margin_pct: float | None = None
    net_margin_pct: float | None = None
    roe_pct: float | None = None
    roic_pct: float | None = None
    free_cash_flow: float | None = None
    free_cash_flow_yield_pct: float | None = None
    debt_to_equity: float | None = None
    net_debt_to_ebitda: float | None = None
    current_ratio: float | None = None

    def __post_init__(self) -> None:
        for name in (
            "score",
            "valuation_score",
            "growth_score",
            "profitability_score",
            "balance_sheet_score",
            "cash_flow_score",
        ):
            _validate_score(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class RiskMetrics:
    score: float | None = None
    volatility_score: float | None = None
    drawdown_score: float | None = None
    tail_risk_score: float | None = None
    market_sensitivity_score: float | None = None
    annual_volatility_pct: float | None = None
    var_95_daily_pct: float | None = None
    maximum_drawdown_pct: float | None = None
    beta: float | None = None
    sharpe_ratio: float | None = None
    atr_pct: float | None = None
    benchmark_correlation: float | None = None

    def __post_init__(self) -> None:
        for name in (
            "score",
            "volatility_score",
            "drawdown_score",
            "tail_risk_score",
            "market_sensitivity_score",
        ):
            _validate_score(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class SentimentMetrics:
    score: float | None = None
    classification: str | None = None
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_score("score", self.score)


@dataclass(frozen=True, slots=True)
class InstitutionalMetrics:
    score: float | None = None
    ownership_pct: float | None = None
    insider_net_activity: float | None = None
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_score("score", self.score)


@dataclass(frozen=True, slots=True)
class CryptoMetrics:
    btc_relative_strength_30d_pct: float | None = None
    volume_change_20d_pct: float | None = None
    average_dollar_volume: float | None = None
    funding_rate_pct: float | None = None
    open_interest: float | None = None
    liquidations_24h: float | None = None
    long_short_ratio: float | None = None
    exchange_netflow: float | None = None
    mvrv: float | None = None
    sopr: float | None = None
    tvl: float | None = None
    active_addresses: float | None = None
    fees_24h: float | None = None
    protocol_revenue_24h: float | None = None

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            _validate_finite(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class MemeCoinMetrics:
    momentum_score: float | None = None
    volume_score: float | None = None
    social_momentum_score: float | None = None
    rvol_20: float | None = None
    volume_change_20d_pct: float | None = None
    average_dollar_volume: float | None = None
    volume_to_market_cap_pct: float | None = None
    dex_liquidity: float | None = None
    holder_growth_30d_pct: float | None = None
    top_holders_concentration_pct: float | None = None
    whale_netflow: float | None = None
    open_interest: float | None = None
    funding_rate_pct: float | None = None
    liquidations_24h: float | None = None

    def __post_init__(self) -> None:
        for name in ("momentum_score", "volume_score", "social_momentum_score"):
            _validate_score(name, getattr(self, name))
        for name in (
            "rvol_20",
            "volume_change_20d_pct",
            "average_dollar_volume",
            "volume_to_market_cap_pct",
            "dex_liquidity",
            "holder_growth_30d_pct",
            "top_holders_concentration_pct",
            "whale_netflow",
            "open_interest",
            "funding_rate_pct",
            "liquidations_24h",
        ):
            _validate_finite(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class StablecoinMetrics:
    peg_health_score: float | None = None
    liquidity_health_score: float | None = None
    issuer_risk_score: float | None = None
    adoption_trend_score: float | None = None
    reserve_transparency_score: float | None = None
    peg_deviation_pct: float | None = None
    max_peg_deviation_30d_pct: float | None = None
    depeg_risk: DepegRisk = DepegRisk.NOT_AVAILABLE
    volume_change_20d_pct: float | None = None
    average_dollar_volume: float | None = None
    market_cap: float | None = None
    market_cap_change_30d_pct: float | None = None
    supply_change_7d_pct: float | None = None
    supply_change_30d_pct: float | None = None
    dex_liquidity: float | None = None
    exchange_liquidity: float | None = None
    chain_distribution_count: int | None = None

    def __post_init__(self) -> None:
        for name in (
            "peg_health_score",
            "liquidity_health_score",
            "issuer_risk_score",
            "adoption_trend_score",
            "reserve_transparency_score",
        ):
            _validate_score(name, getattr(self, name))
        for name in (
            "peg_deviation_pct",
            "max_peg_deviation_30d_pct",
            "volume_change_20d_pct",
            "average_dollar_volume",
            "market_cap",
            "market_cap_change_30d_pct",
            "supply_change_7d_pct",
            "supply_change_30d_pct",
            "dex_liquidity",
            "exchange_liquidity",
            "chain_distribution_count",
        ):
            _validate_finite(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class TradePlan:
    entry_low: float | None = None
    entry_high: float | None = None
    stop: float | None = None
    target_1: float | None = None
    target_2: float | None = None
    risk_reward_1: float | None = None
    risk_reward_2: float | None = None
    sufficient_data: bool = False
    rationale: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        numeric_fields = (
            self.entry_low,
            self.entry_high,
            self.stop,
            self.target_1,
            self.target_2,
            self.risk_reward_1,
            self.risk_reward_2,
        )
        if not self.sufficient_data:
            if any(value is not None for value in numeric_fields):
                raise ValueError("Un plan insuficiente no puede publicar niveles parciales")
            return
        if any(value is None for value in numeric_fields):
            raise ValueError("Un plan suficiente debe incluir todos los niveles y R/R")
        assert self.stop is not None
        assert self.entry_low is not None
        assert self.entry_high is not None
        assert self.target_1 is not None
        assert self.target_2 is not None
        assert self.risk_reward_1 is not None
        assert self.risk_reward_2 is not None
        values = (
            self.stop,
            self.entry_low,
            self.entry_high,
            self.target_1,
            self.target_2,
            self.risk_reward_1,
            self.risk_reward_2,
        )
        if not all(math.isfinite(value) and value > 0 for value in values):
            raise ValueError("Los niveles y R/R deben ser positivos y finitos")
        if not self.stop < self.entry_low <= self.entry_high < self.target_1 < self.target_2:
            raise ValueError("Los niveles del plan long deben estar estrictamente ordenados")
        risk = self.entry_high - self.stop
        if not math.isclose(self.risk_reward_1, (self.target_1 - self.entry_high) / risk):
            raise ValueError("risk_reward_1 no coincide con los niveles")
        if not math.isclose(self.risk_reward_2, (self.target_2 - self.entry_high) / risk):
            raise ValueError("risk_reward_2 no coincide con los niveles")


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    conviction: float | None = None
    technical: float | None = None
    fundamental: float | None = None
    sentiment: float | None = None
    institutional: float | None = None
    risk: float | None = None
    peg_health: float | None = None
    liquidity: float | None = None
    issuer_risk: float | None = None
    adoption: float | None = None

    def __post_init__(self) -> None:
        for name in (
            "conviction",
            "technical",
            "fundamental",
            "sentiment",
            "institutional",
            "risk",
            "peg_health",
            "liquidity",
            "issuer_risk",
            "adoption",
        ):
            _validate_score(name, getattr(self, name))

    def available(self) -> dict[str, float]:
        return {
            name: value
            for name in (
                "technical",
                "fundamental",
                "sentiment",
                "institutional",
                "risk",
                "peg_health",
                "liquidity",
                "issuer_risk",
                "adoption",
            )
            if (value := getattr(self, name)) is not None
        }


@dataclass(frozen=True, slots=True)
class DataConfidence:
    score: float
    coverage_score: float | None = None
    freshness_score: float | None = None
    field_availability_score: float | None = None
    provider_score: float | None = None
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "score",
            "coverage_score",
            "freshness_score",
            "field_availability_score",
            "provider_score",
        ):
            _validate_score(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class DecisionResult:
    action: DecisionAction
    base_action: DecisionAction
    limited_by_data_quality: bool = False
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AssetAnalysis:
    profile: AssetProfile
    market: MarketMetrics = field(default_factory=MarketMetrics)
    technical: TechnicalMetrics | None = None
    fundamental: FundamentalMetrics | None = None
    risk: RiskMetrics | None = None
    sentiment: SentimentMetrics | None = None
    institutional: InstitutionalMetrics | None = None
    crypto: CryptoMetrics | None = None
    meme_coin: MemeCoinMetrics | None = None
    stablecoin: StablecoinMetrics | None = None
    trade_plan: TradePlan | None = None
    scores: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    data_confidence: DataConfidence | None = None
    decision: DecisionAction = DecisionAction.NOT_AVAILABLE
    decision_reasons: tuple[str, ...] = ()
    decision_limited_by_data_quality: bool = False
    positives: tuple[str, ...] = ()
    negatives: tuple[str, ...] = ()
    calculated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.fundamental is not None and not self.profile.supports_corporate_fundamentals:
            raise ValueError("Las métricas corporativas solo son válidas para acciones")
        if self.crypto is not None and self.profile.asset_type is not AssetType.CRYPTO:
            raise ValueError("Las métricas crypto solo son válidas para criptomonedas")
        if self.meme_coin is not None and self.profile.asset_type is not AssetType.MEME_COIN:
            raise ValueError("Las métricas meme solo son válidas para meme coins")
        if self.stablecoin is not None and self.profile.asset_type is not AssetType.STABLECOIN:
            raise ValueError("Las métricas de stablecoin solo son válidas para stablecoins")
