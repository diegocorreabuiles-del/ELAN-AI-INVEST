from __future__ import annotations

import logging
import math
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class TradeResult:
    success: bool
    message: str
    order_id: int | None = None


@dataclass(frozen=True)
class RiskReviewResult:
    success: bool
    message: str
    checked_positions: int = 0
    triggered_symbols: tuple[str, ...] = ()
    order_ids: tuple[int, ...] = ()
    valuation: dict[str, float] | None = None


class PaperTradingEngine:
    """Motor de simulación local. Nunca envía órdenes a un broker real."""

    def __init__(
        self,
        database_path: str | Path,
        initial_capital: float = 100_000.0,
        commission_pct: float = 0.10,
        stop_loss_pct: float = 8.0,
        max_open_positions: int = 8,
        database_timeout_seconds: float = 5.0,
    ) -> None:
        if initial_capital <= 0:
            raise ValueError("El capital inicial debe ser mayor que cero")
        if not 0 <= commission_pct <= 100:
            raise ValueError("La comisión debe estar entre 0 y 100")
        if not 0 < stop_loss_pct <= 100:
            raise ValueError("El stop loss debe estar entre 0 y 100")
        if max_open_positions < 1:
            raise ValueError("Debe permitirse al menos una posición abierta")
        if database_timeout_seconds <= 0:
            raise ValueError("El timeout de base de datos debe ser positivo")

        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initial_capital = float(initial_capital)
        self.commission_pct = float(commission_pct)
        self.stop_loss_pct = float(stop_loss_pct)
        self.max_open_positions = int(max_open_positions)
        self.database_timeout_seconds = float(database_timeout_seconds)
        self._create_schema()
        self._ensure_account()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=self.database_timeout_seconds,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout = {int(self.database_timeout_seconds * 1000)}")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _transaction(self, *, immediate: bool = True) -> Iterator[sqlite3.Connection]:
        """Open an explicit transaction and guarantee commit or rollback."""
        with closing(self._connect()) as connection:
            try:
                connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def _create_schema(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
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

    @staticmethod
    def _database_failure(operation: str, exc: sqlite3.Error) -> TradeResult:
        LOGGER.exception("Paper trading %s transaction failed", operation, exc_info=exc)
        return TradeResult(False, "Operación no guardada por un error de base de datos")

    def _ensure_account(self) -> None:
        with self._transaction() as connection:
            now = self._now()
            connection.execute(
                """
                INSERT OR IGNORE INTO paper_account
                (id, initial_capital, cash, updated_at) VALUES (1, ?, ?, ?)
                """,
                (self.initial_capital, self.initial_capital, now),
            )

    def reset(self) -> None:
        with self._transaction() as connection:
            connection.execute("DELETE FROM paper_positions")
            connection.execute("DELETE FROM paper_orders")
            connection.execute("DELETE FROM paper_equity_snapshots")
            account_update = connection.execute(
                """
                UPDATE paper_account
                SET initial_capital = ?, cash = ?, updated_at = ? WHERE id = 1
                """,
                (self.initial_capital, self.initial_capital, self._now()),
            )
            if account_update.rowcount != 1:
                raise sqlite3.IntegrityError("paper account missing during reset")

    def account(self) -> dict[str, float]:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT initial_capital, cash FROM paper_account WHERE id = 1"
            ).fetchone()
        if row is None:
            raise RuntimeError("La cuenta de paper trading no existe")
        return {
            "initial_capital": float(row["initial_capital"]),
            "cash": float(row["cash"]),
        }

    @staticmethod
    def _positions_frame(
        rows: list[sqlite3.Row], latest_prices: dict[str, float] | None = None
    ) -> pd.DataFrame:
        columns = [
            "symbol",
            "quantity",
            "average_price",
            "stop_price",
            "opened_at",
            "updated_at",
        ]
        frame = pd.DataFrame([dict(row) for row in rows], columns=columns)
        if frame.empty:
            return frame
        latest_prices = latest_prices or {}
        frame["current_price"] = frame.apply(
            lambda row: float(latest_prices.get(row["symbol"], row["average_price"])),
            axis=1,
        )
        frame["market_value"] = frame["quantity"] * frame["current_price"]
        frame["unrealised_pnl"] = (frame["current_price"] - frame["average_price"]) * frame[
            "quantity"
        ]
        frame["return_pct"] = (frame["current_price"] / frame["average_price"] - 1.0) * 100.0
        return frame

    @staticmethod
    def _read_positions(connection: sqlite3.Connection) -> list[sqlite3.Row]:
        return connection.execute("""
            SELECT symbol, quantity, average_price, stop_price, opened_at, updated_at
            FROM paper_positions ORDER BY symbol
            """).fetchall()

    def positions(self, latest_prices: dict[str, float] | None = None) -> pd.DataFrame:
        with closing(self._connect()) as connection:
            rows = self._read_positions(connection)
        return self._positions_frame(rows, latest_prices)

    def orders(self, limit: int = 200) -> pd.DataFrame:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, side, symbol, quantity, price, gross_amount,
                       commission, realised_pnl, reason
                FROM paper_orders ORDER BY id DESC LIMIT ?
                """,
                (max(0, int(limit)),),
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

        try:
            with self._transaction() as connection:
                existing = connection.execute(
                    """
                    SELECT quantity, average_price, opened_at
                    FROM paper_positions WHERE symbol = ?
                    """,
                    (symbol,),
                ).fetchone()
                if existing is None:
                    count = connection.execute(
                        "SELECT COUNT(*) AS n FROM paper_positions"
                    ).fetchone()["n"]
                    if int(count) >= self.max_open_positions:
                        return TradeResult(False, "Máximo de posiciones abiertas alcanzado")
                    new_quantity = quantity
                    new_average = price
                    opened_at = now
                else:
                    old_quantity = float(existing["quantity"])
                    old_average = float(existing["average_price"])
                    new_quantity = old_quantity + quantity
                    new_average = (old_quantity * old_average + quantity * price) / new_quantity
                    opened_at = existing["opened_at"]

                cash_update = connection.execute(
                    """
                    UPDATE paper_account
                    SET cash = cash - ?, updated_at = ?
                    WHERE id = 1 AND cash >= ?
                    """,
                    (total_cost, now, total_cost - 1e-9),
                )
                if cash_update.rowcount != 1:
                    return TradeResult(False, "Liquidez insuficiente")

                stop_price = new_average * (1.0 - self.stop_loss_pct / 100.0)
                connection.execute(
                    """
                    INSERT INTO paper_positions
                    (symbol, quantity, average_price, stop_price, opened_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        quantity = excluded.quantity,
                        average_price = excluded.average_price,
                        stop_price = excluded.stop_price,
                        updated_at = excluded.updated_at
                    """,
                    (
                        symbol,
                        new_quantity,
                        new_average,
                        stop_price,
                        opened_at,
                        now,
                    ),
                )
                cursor = connection.execute(
                    """
                    INSERT INTO paper_orders
                    (created_at, side, symbol, quantity, price, gross_amount,
                     commission, realised_pnl, reason)
                    VALUES (?, 'BUY', ?, ?, ?, ?, ?, 0, ?)
                    """,
                    (
                        now,
                        symbol,
                        quantity,
                        price,
                        amount_eur,
                        commission,
                        reason,
                    ),
                )
                order_id = cursor.lastrowid
                if order_id is None:
                    raise sqlite3.IntegrityError("paper buy order insert did not return an id")
        except sqlite3.Error as exc:
            return self._database_failure("buy", exc)

        return TradeResult(True, f"Compra simulada: {symbol}", order_id)

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
        try:
            with self._transaction() as connection:
                result = self._sell_in_transaction(
                    connection, symbol, quantity, price, reason=reason
                )
        except sqlite3.Error as exc:
            return self._database_failure("sell", exc)
        return result

    def _sell_in_transaction(
        self,
        connection: sqlite3.Connection,
        symbol: str,
        quantity: float,
        price: float,
        *,
        reason: str,
    ) -> TradeResult:
        position = connection.execute(
            """
            SELECT quantity, average_price
            FROM paper_positions WHERE symbol = ?
            """,
            (symbol,),
        ).fetchone()
        if position is None:
            return TradeResult(False, "Posición inexistente")
        held = float(position["quantity"])
        if quantity > held + 1e-9:
            return TradeResult(False, "Cantidad superior a la posición")

        now = self._now()
        gross = quantity * price
        commission = gross * self.commission_pct / 100.0
        proceeds = gross - commission
        realised_pnl = (price - float(position["average_price"])) * quantity - commission
        remaining = held - quantity
        if remaining <= 1e-9:
            position_update = connection.execute(
                "DELETE FROM paper_positions WHERE symbol = ?",
                (symbol,),
            )
        else:
            position_update = connection.execute(
                """
                UPDATE paper_positions
                SET quantity = ?, updated_at = ? WHERE symbol = ?
                """,
                (remaining, now, symbol),
            )
        if position_update.rowcount != 1:
            return TradeResult(False, "La posición cambió durante la venta")

        account_update = connection.execute(
            """
            UPDATE paper_account
            SET cash = cash + ?, updated_at = ? WHERE id = 1
            """,
            (proceeds, now),
        )
        if account_update.rowcount != 1:
            raise sqlite3.IntegrityError("paper account missing during sell")
        cursor = connection.execute(
            """
            INSERT INTO paper_orders
            (created_at, side, symbol, quantity, price, gross_amount,
             commission, realised_pnl, reason)
            VALUES (?, 'SELL', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                symbol,
                quantity,
                price,
                gross,
                commission,
                realised_pnl,
                reason,
            ),
        )
        order_id = cursor.lastrowid
        if order_id is None:
            raise sqlite3.IntegrityError("paper sell order insert did not return an id")
        return TradeResult(True, f"Venta simulada: {symbol}", order_id)

    @staticmethod
    def _validated_risk_prices(
        rows: list[sqlite3.Row], latest_prices: dict[str, float]
    ) -> dict[str, float]:
        validated: dict[str, float] = {}
        for row in rows:
            symbol = str(row["symbol"])
            if symbol not in latest_prices:
                raise ValueError(f"Falta precio actual para {symbol}")
            try:
                price = float(latest_prices[symbol])
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError(f"Precio actual inválido para {symbol}") from exc
            stop_price = row["stop_price"]
            if not math.isfinite(price) or price <= 0:
                raise ValueError(f"Precio actual inválido para {symbol}")
            try:
                parsed_stop = float(stop_price)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError(f"Stop inválido para {symbol}") from exc
            if not math.isfinite(parsed_stop) or parsed_stop <= 0:
                raise ValueError(f"Stop inválido para {symbol}")
            validated[symbol] = price
        return validated

    def review_risk_and_snapshot(self, latest_prices: dict[str, float]) -> RiskReviewResult:
        """Review paper stops and persist the post-review valuation atomically."""
        try:
            with self._transaction() as connection:
                rows = self._read_positions(connection)
                validated_prices = self._validated_risk_prices(rows, latest_prices)
                order_ids: list[int] = []
                triggered_symbols: list[str] = []
                for row in rows:
                    symbol = str(row["symbol"])
                    if validated_prices[symbol] > float(row["stop_price"]):
                        continue
                    result = self._sell_in_transaction(
                        connection,
                        symbol,
                        float(row["quantity"]),
                        validated_prices[symbol],
                        reason="stop_loss",
                    )
                    if not result.success or result.order_id is None:
                        raise RuntimeError(result.message)
                    triggered_symbols.append(symbol)
                    order_ids.append(result.order_id)

                valuation = self._valuation_from_connection(connection, validated_prices)
                connection.execute(
                    """
                    INSERT INTO paper_equity_snapshots
                    (created_at, cash, positions_value, equity) VALUES (?, ?, ?, ?)
                    """,
                    (
                        self._now(),
                        valuation["cash"],
                        valuation["positions_value"],
                        valuation["equity"],
                    ),
                )
        except ValueError as exc:
            return RiskReviewResult(False, str(exc))
        except (sqlite3.Error, RuntimeError) as exc:
            LOGGER.exception("Paper risk review transaction failed", exc_info=exc)
            return RiskReviewResult(False, "Revisión no guardada; no se aplicó ningún cambio")

        message = "Revisión completada y snapshot guardado"
        if triggered_symbols:
            message += f". Stops ejecutados: {', '.join(triggered_symbols)}"
        return RiskReviewResult(
            True,
            message,
            checked_positions=len(rows),
            triggered_symbols=tuple(triggered_symbols),
            order_ids=tuple(order_ids),
            valuation=valuation,
        )

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

    @staticmethod
    def _valuation_from_connection(
        connection: sqlite3.Connection, latest_prices: dict[str, float]
    ) -> dict[str, float]:
        account = connection.execute(
            "SELECT initial_capital, cash FROM paper_account WHERE id = 1"
        ).fetchone()
        if account is None:
            raise RuntimeError("La cuenta de paper trading no existe")
        rows = PaperTradingEngine._read_positions(connection)
        positions_value = sum(
            float(row["quantity"]) * float(latest_prices.get(row["symbol"], row["average_price"]))
            for row in rows
        )
        initial_capital = float(account["initial_capital"])
        cash = float(account["cash"])
        equity = cash + positions_value
        return {
            "initial_capital": initial_capital,
            "cash": cash,
            "positions_value": positions_value,
            "equity": equity,
            "total_return_pct": (equity / initial_capital - 1.0) * 100.0,
        }

    def valuation(self, latest_prices: dict[str, float]) -> dict[str, float]:
        with self._transaction(immediate=False) as connection:
            return self._valuation_from_connection(connection, latest_prices)

    def save_snapshot(self, latest_prices: dict[str, float]) -> dict[str, float]:
        with self._transaction() as connection:
            valuation = self._valuation_from_connection(connection, latest_prices)
            connection.execute(
                """
                INSERT INTO paper_equity_snapshots
                (created_at, cash, positions_value, equity) VALUES (?, ?, ?, ?)
                """,
                (
                    self._now(),
                    valuation["cash"],
                    valuation["positions_value"],
                    valuation["equity"],
                ),
            )
        return valuation

    def equity_history(self) -> pd.DataFrame:
        with closing(self._connect()) as connection:
            rows = connection.execute("""
                SELECT created_at, cash, positions_value, equity
                FROM paper_equity_snapshots ORDER BY id
                """).fetchall()
        frame = pd.DataFrame([dict(row) for row in rows])
        if not frame.empty:
            frame["created_at"] = pd.to_datetime(frame["created_at"], utc=True)
        return frame
