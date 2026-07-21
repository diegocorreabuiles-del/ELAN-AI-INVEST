import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from elan_ai_invest.paper_trading import PaperTradingEngine


def build_engine(database_path: Path, *, max_open_positions: int = 2):
    return PaperTradingEngine(
        database_path,
        initial_capital=100_000,
        commission_pct=0.10,
        stop_loss_pct=8.0,
        max_open_positions=max_open_positions,
    )


def test_concurrent_buys_never_overdraw_cash(tmp_path):
    database_path = tmp_path / "paper.db"
    engines = [build_engine(database_path), build_engine(database_path)]
    barrier = Barrier(2)

    def buy(engine):
        barrier.wait()
        return engine.buy("SPY", amount_eur=60_000, price=500)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(buy, engines))

    assert sum(result.success for result in results) == 1
    assert engines[0].account()["cash"] == pytest.approx(39_940)
    assert len(engines[0].orders()) == 1
    assert engines[0].positions().iloc[0]["quantity"] == pytest.approx(120)


def test_concurrent_sells_cannot_oversell(tmp_path):
    database_path = tmp_path / "paper.db"
    primary = build_engine(database_path)
    assert primary.buy("SPY", amount_eur=10_000, price=500).success
    engines = [primary, build_engine(database_path)]
    barrier = Barrier(2)

    def sell(engine):
        barrier.wait()
        return engine.sell("SPY", quantity=15, price=510)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(sell, engines))

    assert sum(result.success for result in results) == 1
    position = primary.positions().iloc[0]
    assert position["quantity"] == pytest.approx(5)
    assert len(primary.orders()) == 2


def test_concurrent_buys_respect_max_open_positions(tmp_path):
    database_path = tmp_path / "paper.db"
    engines = [
        build_engine(database_path, max_open_positions=1),
        build_engine(database_path, max_open_positions=1),
    ]
    barrier = Barrier(2)

    def buy(payload):
        engine, symbol = payload
        barrier.wait()
        return engine.buy(symbol, amount_eur=5_000, price=500)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(buy, zip(engines, ["SPY", "QQQ"], strict=True)))

    assert sum(result.success for result in results) == 1
    assert len(engines[0].positions()) == 1
    assert len(engines[0].orders()) == 1


def test_waiting_buy_reads_cash_after_writer_commits(tmp_path):
    database_path = tmp_path / "paper.db"
    engine = build_engine(database_path)
    locking_connection = engine._connect()
    locking_connection.execute("BEGIN IMMEDIATE")
    locking_connection.execute("UPDATE paper_account SET cash = 0 WHERE id = 1")

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(engine.buy, "SPY", 1_000, 500)
            time.sleep(0.05)
            locking_connection.commit()
            result = future.result(timeout=5)
    finally:
        locking_connection.close()

    assert not result.success
    assert engine.account()["cash"] == pytest.approx(0)
    assert engine.positions().empty
    assert engine.orders().empty


def test_buy_rolls_back_if_order_insert_fails(tmp_path):
    database_path = tmp_path / "paper.db"
    engine = build_engine(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute("""
            CREATE TRIGGER fail_buy_order
            BEFORE INSERT ON paper_orders
            WHEN NEW.side = 'BUY'
            BEGIN
                SELECT RAISE(ABORT, 'forced buy failure');
            END
            """)

    result = engine.buy("SPY", amount_eur=10_000, price=500)

    assert not result.success
    assert "no guardada" in result.message.lower()
    assert engine.account()["cash"] == pytest.approx(100_000)
    assert engine.positions().empty
    assert engine.orders().empty


def test_sell_rolls_back_if_order_insert_fails(tmp_path):
    database_path = tmp_path / "paper.db"
    engine = build_engine(database_path)
    assert engine.buy("SPY", amount_eur=10_000, price=500).success
    cash_before = engine.account()["cash"]
    with sqlite3.connect(database_path) as connection:
        connection.execute("""
            CREATE TRIGGER fail_sell_order
            BEFORE INSERT ON paper_orders
            WHEN NEW.side = 'SELL'
            BEGIN
                SELECT RAISE(ABORT, 'forced sell failure');
            END
            """)

    result = engine.sell("SPY", quantity=10, price=510)

    assert not result.success
    assert "no guardada" in result.message.lower()
    assert engine.account()["cash"] == pytest.approx(cash_before)
    assert engine.positions().iloc[0]["quantity"] == pytest.approx(20)
    assert len(engine.orders()) == 1


def test_sell_rolls_back_if_account_is_missing(tmp_path):
    database_path = tmp_path / "paper.db"
    engine = build_engine(database_path)
    assert engine.buy("SPY", amount_eur=10_000, price=500).success
    with sqlite3.connect(database_path) as connection:
        connection.execute("DELETE FROM paper_account")

    result = engine.sell("SPY", quantity=20, price=510)

    assert not result.success
    assert "no guardada" in result.message.lower()
    assert engine.positions().iloc[0]["quantity"] == pytest.approx(20)
    assert len(engine.orders()) == 1


def test_reset_rolls_back_if_account_is_missing(tmp_path):
    database_path = tmp_path / "paper.db"
    engine = build_engine(database_path)
    assert engine.buy("SPY", amount_eur=10_000, price=500).success
    with sqlite3.connect(database_path) as connection:
        connection.execute("DELETE FROM paper_account")

    with pytest.raises(sqlite3.IntegrityError, match="account missing"):
        engine.reset()

    assert engine.positions().iloc[0]["quantity"] == pytest.approx(20)
    assert len(engine.orders()) == 1


def test_realised_pnl_and_commissions_are_traceable(tmp_path):
    engine = build_engine(tmp_path / "paper.db")
    assert engine.buy("SPY", amount_eur=10_000, price=500).success
    assert engine.sell("SPY", quantity=10, price=510).success

    orders = engine.orders().sort_values("id")
    assert orders.iloc[0]["commission"] == pytest.approx(10.0)
    assert orders.iloc[1]["commission"] == pytest.approx(5.1)
    assert orders.iloc[1]["realised_pnl"] == pytest.approx(94.9)


def test_snapshot_matches_one_consistent_valuation(tmp_path):
    engine = build_engine(tmp_path / "paper.db")
    assert engine.buy("SPY", amount_eur=10_000, price=500).success

    valuation = engine.save_snapshot({"SPY": 510})
    history = engine.equity_history()

    assert valuation["cash"] == pytest.approx(89_990)
    assert valuation["positions_value"] == pytest.approx(10_200)
    assert valuation["equity"] == pytest.approx(100_190)
    assert len(history) == 1
    assert history.iloc[0]["cash"] == pytest.approx(valuation["cash"])
    assert history.iloc[0]["positions_value"] == pytest.approx(valuation["positions_value"])
    assert history.iloc[0]["equity"] == pytest.approx(valuation["equity"])


def test_risk_review_closes_stop_and_snapshots_post_sale_state(tmp_path):
    engine = build_engine(tmp_path / "paper.db")
    assert engine.buy("SPY", amount_eur=10_000, price=500).success

    result = engine.review_risk_and_snapshot({"SPY": 450})

    assert result.success
    assert result.checked_positions == 1
    assert result.triggered_symbols == ("SPY",)
    assert len(result.order_ids) == 1
    assert result.valuation is not None
    assert result.valuation["cash"] == pytest.approx(98_981)
    assert result.valuation["positions_value"] == pytest.approx(0)
    assert engine.positions().empty
    history = engine.equity_history()
    assert len(history) == 1
    assert history.iloc[0]["equity"] == pytest.approx(result.valuation["equity"])


def test_repeated_risk_review_never_duplicates_stop_sale(tmp_path):
    engine = build_engine(tmp_path / "paper.db")
    assert engine.buy("SPY", amount_eur=10_000, price=500).success

    first = engine.review_risk_and_snapshot({"SPY": 450})
    second = engine.review_risk_and_snapshot({"SPY": 450})

    assert first.success and second.success
    stop_orders = engine.orders().query("reason == 'stop_loss'")
    assert len(stop_orders) == 1
    assert len(engine.equity_history()) == 2


@pytest.mark.parametrize("latest_prices", [{}, {"SPY": 0}, {"SPY": float("nan")}, {"SPY": None}])
def test_risk_review_fails_closed_with_missing_or_invalid_price(tmp_path, latest_prices):
    engine = build_engine(tmp_path / "paper.db")
    assert engine.buy("SPY", amount_eur=10_000, price=500).success
    cash_before = engine.account()["cash"]

    result = engine.review_risk_and_snapshot(latest_prices)

    assert not result.success
    assert engine.account()["cash"] == pytest.approx(cash_before)
    assert len(engine.positions()) == 1
    assert len(engine.orders()) == 1
    assert engine.equity_history().empty


def test_risk_review_fails_closed_with_invalid_stop(tmp_path):
    database_path = tmp_path / "paper.db"
    engine = build_engine(database_path)
    assert engine.buy("SPY", amount_eur=10_000, price=500).success
    with sqlite3.connect(database_path) as connection:
        connection.execute("UPDATE paper_positions SET stop_price = NULL WHERE symbol = 'SPY'")

    result = engine.review_risk_and_snapshot({"SPY": 450})

    assert not result.success
    assert "Stop inválido" in result.message
    assert len(engine.positions()) == 1
    assert len(engine.orders()) == 1
    assert engine.equity_history().empty


def test_risk_review_rolls_back_stop_if_snapshot_insert_fails(tmp_path):
    database_path = tmp_path / "paper.db"
    engine = build_engine(database_path)
    assert engine.buy("SPY", amount_eur=10_000, price=500).success
    cash_before = engine.account()["cash"]
    with sqlite3.connect(database_path) as connection:
        connection.execute("""
            CREATE TRIGGER fail_risk_snapshot
            BEFORE INSERT ON paper_equity_snapshots
            BEGIN
                SELECT RAISE(ABORT, 'forced snapshot failure');
            END
            """)

    result = engine.review_risk_and_snapshot({"SPY": 450})

    assert not result.success
    assert engine.account()["cash"] == pytest.approx(cash_before)
    assert len(engine.positions()) == 1
    assert len(engine.orders()) == 1
    assert engine.equity_history().empty


def test_concurrent_risk_reviews_create_at_most_one_stop_sale(tmp_path):
    database_path = tmp_path / "paper.db"
    primary = build_engine(database_path)
    assert primary.buy("SPY", amount_eur=10_000, price=500).success
    engines = [primary, build_engine(database_path)]
    barrier = Barrier(2)

    def review(engine):
        barrier.wait()
        return engine.review_risk_and_snapshot({"SPY": 450})

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(review, engines))

    assert all(result.success for result in results)
    stop_orders = primary.orders().query("reason == 'stop_loss'")
    assert len(stop_orders) == 1
    assert primary.positions().empty
    assert len(primary.equity_history()) == 2
