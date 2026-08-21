from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from elan_ai_invest.analysis import TradePlan, calculate_trade_plan


def _ohlc(close: np.ndarray) -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=len(close), freq="B")
    return pd.DataFrame(
        {
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.full(len(close), 1_000_000.0),
        },
        index=dates,
    )


def _structured_history() -> pd.DataFrame:
    close = np.array(
        [
            100,
            98,
            96,
            94,
            92,
            94,
            98,
            104,
            110,
            116,
            120,
            116,
            110,
            104,
            100,
            96,
            92,
            95,
            100,
            106,
            112,
            116,
            118,
            114,
            108,
            102,
            98,
            94,
            96,
            100,
            104,
            108,
            110,
            106,
            102,
            99,
            97,
            100,
            103,
            105,
        ],
        dtype=float,
    )
    return _ohlc(close)


def test_trade_plan_uses_observed_structure_and_conservative_risk_reward() -> None:
    history = _structured_history()

    plan = calculate_trade_plan(history)

    assert plan.sufficient_data
    assert plan.stop is not None
    assert plan.entry_low is not None
    assert plan.entry_high is not None
    assert plan.target_1 is not None
    assert plan.target_2 is not None
    assert plan.risk_reward_1 is not None
    assert plan.risk_reward_2 is not None
    assert plan.stop < plan.entry_low <= plan.entry_high < plan.target_1 < plan.target_2
    observed_highs = set(history["High"].astype(float))
    assert plan.target_1 in observed_highs
    assert plan.target_2 in observed_highs
    risk = plan.entry_high - plan.stop
    assert plan.risk_reward_1 == pytest.approx((plan.target_1 - plan.entry_high) / risk)
    assert plan.risk_reward_2 == pytest.approx((plan.target_2 - plan.entry_high) / risk)
    assert plan.risk_reward_2 > plan.risk_reward_1 > 0
    assert all(math.isfinite(value) for value in (plan.risk_reward_1, plan.risk_reward_2))


def test_short_history_returns_no_partial_levels() -> None:
    plan = calculate_trade_plan(_ohlc(np.linspace(100.0, 105.0, 20)))

    assert not plan.sufficient_data
    assert plan.entry_low is None
    assert plan.stop is None
    assert plan.target_1 is None
    assert plan.risk_reward_1 is None
    assert "Histórico insuficiente" in plan.rationale[0]


def test_invalid_ohlc_fails_closed() -> None:
    history = _structured_history()
    history.loc[history.index[20], "Close"] = history.loc[history.index[20], "High"] + 5.0

    plan = calculate_trade_plan(history)

    assert not plan.sufficient_data
    assert "OHLC inválido" in plan.rationale[0]


def test_zero_atr_fails_closed() -> None:
    close = np.full(40, 100.0)
    history = _ohlc(close)
    history["High"] = 100.0
    history["Low"] = 100.0

    plan = calculate_trade_plan(history)

    assert not plan.sufficient_data
    assert "ATR" in plan.rationale[0]


def test_missing_overhead_resistances_fails_closed() -> None:
    history = _structured_history()
    history.loc[history.index[-1], ["Open", "High", "Low", "Close"]] = [
        130.0,
        131.0,
        129.0,
        130.0,
    ]

    plan = calculate_trade_plan(history)

    assert not plan.sufficient_data
    assert "resistencias" in plan.rationale[0]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"lookback": 27},
        {"swing_radius": 0},
        {"entry_atr_multiple": 0},
        {"stop_atr_multiple": -1},
        {"entry_atr_multiple": float("inf")},
    ],
)
def test_invalid_configuration_is_rejected(kwargs: dict[str, float | int]) -> None:
    with pytest.raises(ValueError):
        calculate_trade_plan(_structured_history(), **kwargs)


def test_incomplete_contract_cannot_publish_partial_levels() -> None:
    with pytest.raises(ValueError, match="niveles parciales"):
        TradePlan(entry_low=100.0)


def test_sufficient_contract_requires_all_levels() -> None:
    with pytest.raises(ValueError, match="todos los niveles"):
        TradePlan(sufficient_data=True)


def test_contract_rejects_inconsistent_risk_reward() -> None:
    with pytest.raises(ValueError, match="risk_reward_1"):
        TradePlan(
            entry_low=100.0,
            entry_high=101.0,
            stop=98.0,
            target_1=106.0,
            target_2=110.0,
            risk_reward_1=99.0,
            risk_reward_2=3.0,
            sufficient_data=True,
        )
