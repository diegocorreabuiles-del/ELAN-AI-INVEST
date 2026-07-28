from pathlib import Path

import pytest

from elan_ai_invest.core.config import ScoringConfig, load_settings


def test_settings_file_loads():
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root / "config" / "settings.yaml")
    assert settings.app.version == "1.3.0rc1"
    assert settings.market.provider == "yahoo"
    assert settings.market.benchmark == "SPY"
    assert settings.backtest.commission_pct == pytest.approx(0.10)
    assert settings.backtest.slippage_pct == pytest.approx(0.05)


def test_scoring_weights_must_sum_one():
    with pytest.raises(ValueError):
        ScoringConfig(
            trend_weight=0.5,
            momentum_weight=0.5,
            volatility_weight=0.5,
            drawdown_weight=0.5,
        )
