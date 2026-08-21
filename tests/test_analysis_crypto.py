from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from elan_ai_invest.analysis import (
    DepegRisk,
    calculate_crypto_metrics,
    calculate_meme_coin_metrics,
    calculate_stablecoin_metrics,
)


def _history(
    close: np.ndarray,
    *,
    volume: np.ndarray | None = None,
    spread: float = 0.01,
) -> pd.DataFrame:
    index = pd.bdate_range("2025-01-01", periods=len(close))
    observed_volume = volume if volume is not None else np.full(len(close), 1_000_000.0)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close + spread,
            "Low": close - spread,
            "Close": close,
            "Volume": observed_volume,
        },
        index=index,
    )


def test_crypto_metrics_use_aligned_btc_relative_strength_and_observed_volume() -> None:
    asset_close = np.linspace(100.0, 140.0, 60)
    btc_close = np.linspace(100.0, 120.0, 60)
    volume = np.concatenate((np.full(40, 1_000_000.0), np.full(20, 2_000_000.0)))

    result = calculate_crypto_metrics(
        _history(asset_close, volume=volume),
        _history(btc_close)["Close"],
    )

    assert result.btc_relative_strength_30d_pct is not None
    assert result.btc_relative_strength_30d_pct > 0
    assert result.volume_change_20d_pct == pytest.approx(100.0)
    assert result.average_dollar_volume is not None
    assert result.funding_rate_pct is None
    assert result.mvrv is None


def test_crypto_metrics_do_not_invent_absent_benchmark_or_derivatives() -> None:
    result = calculate_crypto_metrics(_history(np.linspace(100.0, 120.0, 60)))

    assert result.btc_relative_strength_30d_pct is None
    assert result.open_interest is None
    assert result.liquidations_24h is None
    assert result.exchange_netflow is None


def test_meme_metrics_reuse_technical_families_but_leave_external_data_unavailable() -> None:
    x = np.arange(260, dtype=float)
    close = 1.0 + x * 0.002 + np.sin(x / 6) * 0.03
    volume = 1_000_000 + (np.sin(x / 8) + 1) * 200_000

    result = calculate_meme_coin_metrics(_history(close, volume=volume, spread=0.02))

    assert result.momentum_score is not None
    assert result.volume_score is not None
    assert result.rvol_20 is not None
    assert result.average_dollar_volume is not None
    assert result.dex_liquidity is None
    assert result.top_holders_concentration_pct is None
    assert result.social_momentum_score is None


def test_stablecoin_metrics_measure_peg_without_inferring_reserves_or_supply() -> None:
    close = np.ones(60)
    close[-1] = 1.001

    result = calculate_stablecoin_metrics(_history(close, spread=0.002))

    assert result.peg_deviation_pct == pytest.approx(0.1)
    assert result.max_peg_deviation_30d_pct == pytest.approx(0.1)
    assert result.peg_health_score == pytest.approx(91.75)
    assert result.depeg_risk is DepegRisk.LOW
    assert result.issuer_risk_score is None
    assert result.reserve_transparency_score is None
    assert result.supply_change_30d_pct is None


def test_stablecoin_metrics_classify_observed_depeg_conservatively() -> None:
    close = np.ones(60)
    close[-1] = 0.95

    result = calculate_stablecoin_metrics(_history(close, spread=0.002))

    assert result.depeg_risk is DepegRisk.CRITICAL
    assert result.peg_health_score == 0.0


def test_invalid_volume_window_returns_unavailable_instead_of_zero() -> None:
    close = np.linspace(10.0, 12.0, 60)
    volume = np.full(60, 1_000_000.0)
    volume[-1] = 0.0

    crypto = calculate_crypto_metrics(_history(close, volume=volume))
    stablecoin = calculate_stablecoin_metrics(_history(np.ones(60), volume=volume, spread=0.002))

    assert crypto.volume_change_20d_pct is None
    assert stablecoin.volume_change_20d_pct is None
