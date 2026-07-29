from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from elan_ai_invest.core.bootstrap import build_core_engine
from elan_ai_invest.core.config import MarketConfig, load_settings
from elan_ai_invest.market.cache import MarketCache
from elan_ai_invest.market_data import download_adjusted_close


def _market_frame(rows: int = 65) -> pd.DataFrame:
    index = pd.date_range("2025-01-01", periods=rows, freq="B")
    return pd.DataFrame({"Close": range(100, 100 + rows)}, index=index)


def test_market_download_retries_with_exponential_backoff_and_timeout():
    calls: list[dict] = []
    delays: list[float] = []

    def flaky_downloader(symbol, **kwargs):
        calls.append({"symbol": symbol, **kwargs})
        if len(calls) < 3:
            raise TimeoutError("servicio temporalmente no disponible")
        return _market_frame()

    result = download_adjusted_close(
        ["spy"],
        minimum_history=60,
        timeout_seconds=7.5,
        max_retries=2,
        backoff_seconds=0.25,
        downloader=flaky_downloader,
        sleep=delays.append,
    )

    assert result.errors == {}
    assert list(result.prices.columns) == ["SPY"]
    assert [call["timeout"] for call in calls] == [7.5, 7.5, 7.5]
    assert delays == [0.25, 0.5]
    assert result.quality is not None
    assert result.quality.provider == "Yahoo"
    assert result.quality.assets["SPY"].source == "provider"


def test_market_download_reports_exhausted_retries_without_inventing_data():
    attempts = 0

    def unavailable_downloader(symbol, **kwargs):
        nonlocal attempts
        attempts += 1
        raise TimeoutError("timeout controlado")

    result = download_adjusted_close(
        ["SPY"],
        max_retries=1,
        backoff_seconds=0,
        downloader=unavailable_downloader,
        sleep=lambda _: None,
    )

    assert attempts == 2
    assert result.prices.empty
    assert result.errors == {"SPY": "descarga fallida tras 2 intentos: timeout controlado"}


def test_safe_csv_cache_avoids_network_and_path_traversal(tmp_path: Path):
    cache = MarketCache(tmp_path, ttl_seconds=3600)
    network_calls = 0

    def downloader(symbol, **kwargs):
        nonlocal network_calls
        network_calls += 1
        return _market_frame()

    first = download_adjusted_close(
        ["../SPY"],
        minimum_history=60,
        cache=cache,
        downloader=downloader,
        quality_now=datetime(2025, 4, 5, tzinfo=UTC),
    )
    second = download_adjusted_close(
        ["../SPY"],
        minimum_history=60,
        cache=cache,
        downloader=downloader,
        quality_now=datetime(2025, 4, 5, tzinfo=UTC),
    )

    assert first.errors == second.errors == {}
    assert network_calls == 1
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    assert files[0].suffix == ".csv"
    assert files[0].parent == tmp_path
    assert not list(tmp_path.glob("*.pkl"))
    assert first.quality is not None
    assert second.quality is not None
    assert first.quality.assets["../SPY"].source == "provider"
    assert second.quality.assets["../SPY"].source == "cache"


def test_market_cache_ignores_expired_or_corrupt_entries(tmp_path: Path):
    now = 10_000.0
    cache = MarketCache(tmp_path, ttl_seconds=60, clock=lambda: now)
    cache.save("SPY", _market_frame(), "2y", "1d")
    path = next(tmp_path.glob("*.csv"))
    os.utime(path, (now - 120, now - 120))

    assert cache.load("SPY", "2y", "1d") is None

    path.write_text('"unterminated', encoding="utf-8")
    cache = MarketCache(tmp_path, ttl_seconds=60, clock=lambda: path.stat().st_mtime)
    assert cache.load("SPY", "2y", "1d") is None


def test_market_resilience_settings_are_loaded_and_cache_stays_inside_project():
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root / "config" / "settings.yaml")

    assert settings.market.timeout_seconds == 10
    assert settings.market.max_retries == 2
    assert settings.market.backoff_seconds == pytest.approx(0.5)
    assert settings.market.cache_ttl_seconds == 3600
    assert settings.market.cache_directory == "data/market_cache"
    with pytest.raises(ValueError, match="dentro del proyecto"):
        MarketConfig(cache_directory="../outside")


def test_bootstrap_wires_market_resilience_settings(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        """
market:
  provider: yahoo
  timeout_seconds: 4
  max_retries: 3
  backoff_seconds: 0.2
  cache_ttl_seconds: 900
  cache_directory: data/quotes
logging:
  file_path: logs/test.log
""".strip(),
        encoding="utf-8",
    )

    engine = build_core_engine(tmp_path)

    assert engine.provider.timeout_seconds == 4
    assert engine.provider.max_retries == 3
    assert engine.provider.backoff_seconds == pytest.approx(0.2)
    assert engine.provider.cache.ttl_seconds == 900
    assert engine.provider.cache.cache_dir == tmp_path / "data" / "quotes"
