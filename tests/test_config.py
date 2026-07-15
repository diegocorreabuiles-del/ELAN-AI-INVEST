from pathlib import Path

import pytest

from elan_ai_invest.core.config import ScoringConfig, load_settings


def test_settings_file_loads():
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root / "config" / "settings.yaml")
    assert settings.app.version == "0.7.0"
    assert settings.market.provider == "yahoo"


def test_scoring_weights_must_sum_one():
    with pytest.raises(ValueError):
        ScoringConfig(
            trend_weight=0.5,
            momentum_weight=0.5,
            volatility_weight=0.5,
            drawdown_weight=0.5,
        )
