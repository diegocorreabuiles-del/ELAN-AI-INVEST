from pathlib import Path

import pytest

from elan_ai_invest.paper_trading import PaperTradingEngine


def build_engine(tmp_path: Path) -> PaperTradingEngine:
    return PaperTradingEngine(
        tmp_path / "paper.db",
        initial_capital=100_000,
        commission_pct=0.10,
        stop_loss_pct=8.0,
        max_open_positions=2,
    )


def test_buy_and_sell_updates_cash_and_position(tmp_path):
    engine = build_engine(tmp_path)
    result = engine.buy("SPY", amount_eur=10_000, price=500)
    assert result.success
    positions = engine.positions({"SPY": 510})
    assert len(positions) == 1
    assert positions.iloc[0]["quantity"] == pytest.approx(20)
    assert engine.account()["cash"] == pytest.approx(89_990)

    result = engine.sell("SPY", quantity=10, price=510)
    assert result.success
    positions = engine.positions({"SPY": 510})
    assert positions.iloc[0]["quantity"] == pytest.approx(10)
    assert engine.account()["cash"] == pytest.approx(95_084.9)


def test_rejects_purchase_without_cash(tmp_path):
    engine = build_engine(tmp_path)
    result = engine.buy("SPY", amount_eur=100_000, price=500)
    assert not result.success
    assert "Liquidez" in result.message


def test_stop_loss_closes_position(tmp_path):
    engine = build_engine(tmp_path)
    engine.buy("QQQ", amount_eur=10_000, price=500)
    results = engine.apply_stop_losses({"QQQ": 450})
    assert len(results) == 1
    assert results[0].success
    assert engine.positions({"QQQ": 450}).empty
    orders = engine.orders()
    assert set(orders["side"]) == {"BUY", "SELL"}
    assert "stop_loss" in set(orders["reason"])


def test_max_open_positions(tmp_path):
    engine = build_engine(tmp_path)
    assert engine.buy("SPY", 5_000, 500).success
    assert engine.buy("QQQ", 5_000, 500).success
    result = engine.buy("GLD", 5_000, 250)
    assert not result.success
    assert "Máximo" in result.message


def test_reset_restores_initial_capital(tmp_path):
    engine = build_engine(tmp_path)
    engine.buy("SPY", 5_000, 500)
    engine.reset()
    assert engine.positions().empty
    assert engine.orders().empty
    assert engine.account()["cash"] == pytest.approx(100_000)
