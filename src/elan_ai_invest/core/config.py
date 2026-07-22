from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from elan_ai_invest import __version__


class AppConfig(BaseModel):
    name: str = "ELAN AI INVEST"
    version: str = __version__
    environment: str = "development"

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if value != __version__:
            raise ValueError(
                f"La versión configurada debe coincidir con el paquete ({__version__})"
            )
        return value


class MarketConfig(BaseModel):
    provider: str = "yahoo"
    period: str = "2y"
    interval: str = "1d"
    minimum_history: int = Field(default=210, ge=60)
    benchmark: str = "SPY"
    timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    max_retries: int = Field(default=2, ge=0, le=10)
    backoff_seconds: float = Field(default=0.5, ge=0, le=60)
    cache_ttl_seconds: int = Field(default=3600, ge=0, le=604800)
    cache_directory: str = "data/market_cache"

    @field_validator("cache_directory")
    @classmethod
    def validate_cache_directory(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("La caché de mercado debe permanecer dentro del proyecto")
        return value


class ScoringConfig(BaseModel):
    trend_weight: float = 0.40
    momentum_weight: float = 0.35
    volatility_weight: float = 0.15
    drawdown_weight: float = 0.10

    @model_validator(mode="after")
    def validate_weights(self) -> ScoringConfig:
        total = (
            self.trend_weight + self.momentum_weight + self.volatility_weight + self.drawdown_weight
        )
        if abs(total - 1.0) > 1e-9:
            raise ValueError("Los pesos de scoring deben sumar 1.0")
        return self


class BacktestConfig(BaseModel):
    lookback: int = Field(default=63, ge=21)
    top_n: int = Field(default=3, ge=1)
    rebalance_days: int = Field(default=21, ge=1)
    commission_pct: float = Field(default=0.10, ge=0, le=5)
    slippage_pct: float = Field(default=0.05, ge=0, le=5)


class RiskConfig(BaseModel):
    confidence_levels: list[float] = [0.95, 0.99]
    annualisation_days: int = Field(default=252, ge=200, le=366)
    risk_budget_per_position_pct: float = Field(default=0.50, gt=0, le=5)
    max_position_pct: float = Field(default=15.0, gt=0, le=100)
    max_portfolio_volatility_pct: float = Field(default=20.0, gt=0)


class PortfolioConfig(BaseModel):
    initial_capital: float = Field(default=100_000.0, gt=0)
    profile: str = "moderado"
    min_score: float = Field(default=55.0, ge=0, le=100)
    max_positions: int = Field(default=8, ge=1)
    max_position_pct: float = Field(default=15.0, gt=0, le=100)
    min_cash_pct: float = Field(default=20.0, ge=0, le=100)


class PaperTradingConfig(BaseModel):
    enabled: bool = True
    initial_capital: float = Field(default=100_000.0, gt=0)
    commission_pct: float = Field(default=0.10, ge=0, le=5)
    stop_loss_pct: float = Field(default=8.0, gt=0, le=100)
    max_open_positions: int = Field(default=8, ge=1)
    database_path: str = "data/paper_trading.db"


class StorageConfig(BaseModel):
    database_path: str = "data/elan_ai_invest.db"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file_path: str = "logs/elan_ai_invest.log"
    max_bytes: int = 2_000_000
    backup_count: int = 5


class Settings(BaseModel):
    app: AppConfig = AppConfig()
    market: MarketConfig = MarketConfig()
    scoring: ScoringConfig = ScoringConfig()
    backtest: BacktestConfig = BacktestConfig()
    risk: RiskConfig = RiskConfig()
    portfolio: PortfolioConfig = PortfolioConfig()
    paper_trading: PaperTradingConfig = PaperTradingConfig()
    storage: StorageConfig = StorageConfig()
    logging: LoggingConfig = LoggingConfig()


def load_settings(path: Path) -> Settings:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de configuración: {path}")
    with path.open("r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}
    return Settings.model_validate(raw)
