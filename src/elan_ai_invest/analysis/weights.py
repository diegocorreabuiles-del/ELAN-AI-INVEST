from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType

from .models import AssetType


class ScoreComponent(StrEnum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    INSTITUTIONAL = "institutional"
    RISK = "risk"
    PEG_HEALTH = "peg_health"
    LIQUIDITY = "liquidity"
    ISSUER_RISK = "issuer_risk"
    ADOPTION = "adoption"


def _weights(**values: float) -> Mapping[ScoreComponent, float]:
    return MappingProxyType({ScoreComponent(name): weight for name, weight in values.items()})


ASSET_SCORE_WEIGHTS: Mapping[AssetType, Mapping[ScoreComponent, float]] = MappingProxyType(
    {
        AssetType.EQUITY: _weights(
            technical=0.25,
            fundamental=0.30,
            sentiment=0.15,
            institutional=0.10,
            risk=0.20,
        ),
        AssetType.ETF: _weights(technical=0.45, sentiment=0.10, risk=0.45),
        AssetType.CRYPTO: _weights(
            technical=0.35,
            sentiment=0.20,
            institutional=0.15,
            risk=0.30,
        ),
        AssetType.MEME_COIN: _weights(
            technical=0.40,
            sentiment=0.25,
            institutional=0.10,
            risk=0.25,
        ),
        AssetType.STABLECOIN: _weights(
            peg_health=0.35,
            liquidity=0.25,
            issuer_risk=0.25,
            adoption=0.15,
        ),
        AssetType.FOREX: _weights(technical=0.55, risk=0.45),
        AssetType.BOND: _weights(technical=0.35, sentiment=0.10, risk=0.55),
        AssetType.COMMODITY: _weights(technical=0.50, sentiment=0.15, risk=0.35),
        AssetType.INDEX: _weights(technical=0.50, sentiment=0.10, risk=0.40),
        AssetType.FUND: _weights(technical=0.45, sentiment=0.10, risk=0.45),
        AssetType.UNKNOWN: _weights(technical=0.50, risk=0.50),
    }
)


def weights_for_asset(asset_type: AssetType) -> Mapping[ScoreComponent, float]:
    return ASSET_SCORE_WEIGHTS[asset_type]
