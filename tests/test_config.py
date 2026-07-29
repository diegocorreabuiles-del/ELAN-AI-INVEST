from pathlib import Path

import pytest

from elan_ai_invest.core.config import NewsConfig, ScoringConfig, load_settings


def test_settings_file_loads():
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root / "config" / "settings.yaml")
    assert settings.app.version == "1.3.0rc1"
    assert settings.market.provider == "yahoo"
    assert settings.market.benchmark == "SPY"
    assert settings.backtest.commission_pct == pytest.approx(0.10)
    assert settings.backtest.slippage_pct == pytest.approx(0.05)
    assert settings.news.enabled is True
    assert settings.news.max_items == 10
    assert settings.news.cache_ttl_seconds == 900


def test_scoring_weights_must_sum_one():
    with pytest.raises(ValueError):
        ScoringConfig(
            trend_weight=0.5,
            momentum_weight=0.5,
            volatility_weight=0.5,
            drawdown_weight=0.5,
        )


def test_news_settings_are_bounded():
    with pytest.raises(ValueError):
        NewsConfig(max_items=0)
    with pytest.raises(ValueError):
        NewsConfig(max_items=51)
    with pytest.raises(ValueError):
        NewsConfig(cache_ttl_seconds=59)
