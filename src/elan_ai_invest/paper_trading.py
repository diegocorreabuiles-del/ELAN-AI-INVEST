from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class TradeResult:
    success: bool
    message: str
    order_id: int | None = None


class PaperTradingEngine:
    """Motor de simulación. Nunca envía órdenes a un broker real."""

    def __init__(
        self,
        database_path: str | Path,
        initial_capital: float = 100_000.0,
        commission_pct: float = 0.10,
        stop_loss_pct: float = 8.0,
        max_open_positions: int = 8,
    ) -> None:
        if initial_capital <= 0:
            raise ValueError("El capital inicial debe ser mayor que cero")
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initial_capital = float(initial_capital)
        self.commission_pct = float(commission_pct)
        self.stop_loss_pct = float(stop_loss_pct)
        self.max_open_positions = int(max_open_positions)
        self._create_schema()
        self._ensure_account()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS paper_account (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    initial_capital REAL NOT NULL,
                    cash REAL NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS paper_positions (
                    symbol TEXT PRIMARY KEY,
                    quantity REAL NOT NULL,
                    average_price REAL NOT NULL,
                    stop_price REAL,
                    opened_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS paper_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    side TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    gross_amount REAL NOT NULL,
                    commission REAL NOT NULL,
                    realised_pnl REAL NOT NULL DEFAULT 0,
                    reason TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS paper_equity_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    cash REAL NOT NULL,
                    positions_value REAL NOT NULL,
                    equity REAL NOT NULL
                );
                """)

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def _ensure_account(self) -> None:
        with self._connect() as connection:
            row = connection.execute("SELECT id FROM paper_account WHERE id = 1").fetchone()
            if row is None:
                now = self._now()
                connection.execute(
                    "INSERT INTO paper_account (id, initial_capital, cash, updated_at) VALUES (1, ?, ?, ?)",
                    (self.initial_capital, self.initial_capital, now),
                )

    def reset(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM paper_positions")
            connection.execute("DELETE FROM paper_orders")
            connection.execute("DELETE FROM paper_equity_snapshots")
            connection.execute(
                "UPDATE paper_account SET initial_capital = ?, cash = ?, updated_at = ? WHERE id = 1",
                (self.initial_capital, self.initial_capital, self._now()),
            )

    def account(self) -> dict[str, float]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT initial_capital, cash FROM paper_account WHERE id = 1"
            ).fetchone()
        return {"initial_capital": float(row["initial_capital"]), "cash": float(row["cash"])}

    def positions(self, latest_prices: dict[str, float] | None = None) -> pd.DataFrame:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT symbol, quantity, average_price, stop_price, opened_at, updated_at FROM paper_positions ORDER BY symbol"
            ).fetchall()
        columns = ["symbol", "quantity", "average_price", "stop_price", "opened_at", "updated_at"]
        frame = pd.DataFrame([dict(row) for row in rows], columns=columns)
        if frame.empty:
            return frame
        latest_prices = latest_prices or {}
        frame["current_price"] = frame.apply(
            lambda row: float(latest_prices.get(row["symbol"], row["average_price"])), axis=1
        )
        frame["market_value"] = frame["quantity"] * frame["current_price"]
        frame["unrealised_pnl"] = (frame["current_price"] - frame["average_price"]) * frame[
            "quantity"
        ]
        frame["return_pct"] = (frame["current_price"] / frame["average_price"] - 1.0) * 100.0
        return frame

    def orders(self, limit: int = 200) -> pd.DataFrame:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, side, symbol, quantity, price, gross_amount,
                       commission, realised_pnl, reason
                FROM paper_orders ORDER BY id DESC LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return pd.DataFrame([dict(row) for row in rows])

    def buy(
        self, symbol: str, amount_eur: float, price: float, reason: str = "manual"
    ) -> TradeResult:
        symbol = symbol.strip().upper()
        if not symbol or amount_eur <= 0 or price <= 0:
            return TradeResult(False, "Datos de compra inválidos")

        commission = amount_eur * self.commission_pct / 100.0
        total_cost = amount_eur + commission
        quantity = amount_eur / price
        now = self._now()

        with self._connect() as connection:
            account = connection.execute("SELECT cash FROM paper_account WHERE id = 1").fetchone()
            if float(account["cash"]) + 1e-9 < total_cost:
                return TradeResult(False, "Liquidez insuficiente")

            existing = connection.execute(
                "SELECT quantity, average_price FROM paper_positions WHERE symbol = ?", (symbol,)
            ).fetchone()
            count = connection.execute("SELECT COUNT(*) AS n FROM paper_positions").fetchone()["n"]
            if existing is None and int(count) >= self.max_open_positions:
                return TradeResult(False, "Máximo de posiciones abiertas alcanzado")

            if existing is None:
                new_quantity = quantity
                new_average = price
                opened_at = now
            else:
                old_quantity = float(existing["quantity"])
                old_average = float(existing["average_price"])
                new_quantity = old_quantity + quantity
                new_average = (old_quantity * old_average + quantity * price) / new_quantity
                opened = connection.execute(
                    "SELECT opened_at FROM paper_positions WHERE symbol = ?", (symbol,)
                ).fetchone()
                opened_at = opened["opened_at"]

            stop_price = new_average * (1.0 - self.stop_loss_pct / 100.0)
            connection.execute(
                """
                INSERT INTO paper_positions (symbol, quantity, average_price, stop_price, opened_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    quantity = excluded.quantity,
                    average_price = excluded.average_price,
                    stop_price = excluded.stop_price,
                    updated_at = excluded.updated_at
                """,
                (symbol, new_quantity, new_average, stop_price, opened_at, now),
            )
            connection.execute(
                "UPDATE paper_account SET cash = cash - ?, updated_at = ? WHERE id = 1",
                (total_cost, now),
            )
            cursor = connection.execute(
                """
                INSERT INTO paper_orders
                (created_at, side, symbol, quantity, price, gross_amount, commission, realised_pnl, reason)
                VALUES (?, 'BUY', ?, ?, ?, ?, ?, 0, ?)
                """,
                (now, symbol, quantity, price, amount_eur, commission, reason),
            )
        return TradeResult(True, f"Compra simulada: {symbol}", int(cursor.lastrowid))

    def sell(
        self,
        symbol: str,
        quantity: float,
        price: float,
        reason: str = "manual",
    ) -> TradeResult:
        symbol = symbol.strip().upper()
        if not symbol or quantity <= 0 or price <= 0:
            return TradeResult(False, "Datos de venta inválidos")
        now = self._now()

        with self._connect() as connection:
            position = connection.execute(
                "SELECT quantity, average_price FROM paper_positions WHERE symbol = ?", (symbol,)
            ).fetchone()
            if position is None:
                return TradeResult(False, "Posición inexistente")
            held = float(position["quantity"])
            if quantity > held + 1e-9:
                return TradeResult(False, "Cantidad superior a la posición")

            gross = quantity * price
            commission = gross * self.commission_pct / 100.0
            proceeds = gross - commission
            realised_pnl = (price - float(position["average_price"])) * quantity - commission
            remaining = held - quantity
            if remaining <= 1e-9:
                connection.execute("DELETE FROM paper_positions WHERE symbol = ?", (symbol,))
            else:
                connection.execute(
                    "UPDATE paper_positions SET quantity = ?, updated_at = ? WHERE symbol = ?",
                    (remaining, now, symbol),
                )
            connection.execute(
                "UPDATE paper_account SET cash = cash + ?, updated_at = ? WHERE id = 1",
                (proceeds, now),
            )
            cursor = connection.execute(
                """
                INSERT INTO paper_orders
                (created_at, side, symbol, quantity, price, gross_amount, commission, realised_pnl, reason)
                VALUES (?, 'SELL', ?, ?, ?, ?, ?, ?, ?)
                """,
                (now, symbol, quantity, price, gross, commission, realised_pnl, reason),
            )
        return TradeResult(True, f"Venta simulada: {symbol}", int(cursor.lastrowid))

    def apply_stop_losses(self, latest_prices: dict[str, float]) -> list[TradeResult]:
        positions = self.positions(latest_prices)
        results: list[TradeResult] = []
        if positions.empty:
            return results
        for _, row in positions.iterrows():
            if float(row["current_price"]) <= float(row["stop_price"]):
                results.append(
                    self.sell(
                        row["symbol"],
                        float(row["quantity"]),
                        float(row["current_price"]),
                        reason="stop_loss",
                    )
                )
        return results

    def valuation(self, latest_prices: dict[str, float]) -> dict[str, float]:
        account = self.account()
        positions = self.positions(latest_prices)
        positions_value = 0.0 if positions.empty else float(positions["market_value"].sum())
        equity = account["cash"] + positions_value
        total_return_pct = (equity / account["initial_capital"] - 1.0) * 100.0
        return {
            "initial_capital": account["initial_capital"],
            "cash": account["cash"],
            "positions_value": positions_value,
            "equity": equity,
            "total_return_pct": total_return_pct,
        }

    def save_snapshot(self, latest_prices: dict[str, float]) -> dict[str, float]:
        valuation = self.valuation(latest_prices)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO paper_equity_snapshots (created_at, cash, positions_value, equity)
                VALUES (?, ?, ?, ?)
                """,
                (self._now(), valuation["cash"], valuation["positions_value"], valuation["equity"]),
            )
        return valuation

    def equity_history(self) -> pd.DataFrame:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT created_at, cash, positions_value, equity FROM paper_equity_snapshots ORDER BY id"
            ).fetchall()
        frame = pd.DataFrame([dict(row) for row in rows])
        if not frame.empty:
            frame["created_at"] = pd.to_datetime(frame["created_at"], utc=True)
        return frame
