from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator


class AppConfig(BaseModel):
    name: str = "ELAN AI INVEST"
    version: str = "0.3.0"
    environment: str = "development"


class MarketConfig(BaseModel):
    provider: str = "yahoo"
    period: str = "2y"
    interval: str = "1d"
    minimum_history: int = Field(default=210, ge=60)
    benchmark: str = "SPY"


class ScoringConfig(BaseModel):
    trend_weight: float = 0.40
    momentum_weight: float = 0.35
    volatility_weight: float = 0.15
    drawdown_weight: float = 0.10

    @model_validator(mode="after")
    def validate_weights(self) -> "ScoringConfig":
        total = (
            self.trend_weight
            + self.momentum_weight
            + self.volatility_weight
            + self.drawdown_weight
        )
        if abs(total - 1.0) > 1e-9:
            raise ValueError("Los pesos de scoring deben sumar 1.0")
        return self


class BacktestConfig(BaseModel):
    lookback: int = Field(default=63, ge=21)
    top_n: int = Field(default=3, ge=1)
    rebalance_days: int = Field(default=21, ge=1)


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
    storage: StorageConfig = StorageConfig()
    logging: LoggingConfig = LoggingConfig()


def load_settings(path: Path) -> Settings:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de configuración: {path}")
    with path.open("r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}
    return Settings.model_validate(raw)
