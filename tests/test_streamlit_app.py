from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import streamlit as st
import yfinance as yf
from streamlit.testing.v1 import AppTest

import elan_ai_invest.core.bootstrap as bootstrap
import elan_ai_invest.dashboard.fundamental as fundamental_dashboard
import elan_ai_invest.dashboard.history as history_dashboard
import elan_ai_invest.dashboard.market as market_dashboard
import elan_ai_invest.paper_trading as paper_module
from elan_ai_invest.core.config import Settings
from elan_ai_invest.core.models import AnalysisRequest, AnalysisResult
from elan_ai_invest.fundamental.models import FundamentalAnalysis, FundamentalSnapshot
from elan_ai_invest.market.quality import assess_market_data_quality
from elan_ai_invest.paper_trading import RiskReviewResult, TradeResult

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"
APP_TEST_TIMEOUT = 60
TAB_LABELS = (
    "Mercado",
    "Inteligencia",
    "Fundamental",
    "Ranking",
    "Riesgo",
    "Cartera",
    "Institucional",
    "Paper Trading",
    "Backtesting",
    "Histórico",
    "Sistema",
)


class FakeEngine:
    def __init__(self, settings: Settings, result: AnalysisResult) -> None:
        self.settings = settings
        self.result = result
        self.failure: Exception | None = None
        self.requests: list[AnalysisRequest] = []

    def run_analysis(self, request: AnalysisRequest) -> AnalysisResult:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        return self.result


class FakePaperTradingEngine:
    buy_calls = 0
    sell_calls = 0
    review_calls = 0

    def __init__(self, *args, **kwargs) -> None:
        del args, kwargs

    @classmethod
    def reset(cls) -> None:
        cls.buy_calls = 0
        cls.sell_calls = 0
        cls.review_calls = 0

    def valuation(self, latest_prices: dict[str, float]) -> dict[str, float]:
        del latest_prices
        return {
            "equity": 101_000.0,
            "cash": 80_000.0,
            "positions_value": 21_000.0,
            "total_return_pct": 1.0,
        }

    def positions(self, latest_prices: dict[str, float]) -> pd.DataFrame:
        current_price = float(latest_prices["AAPL"])
        return pd.DataFrame(
            [
                {
                    "symbol": "AAPL",
                    "quantity": 10.0,
                    "average_price": 140.0,
                    "current_price": current_price,
                    "market_value": current_price * 10,
                    "unrealised_pnl": 100.0,
                    "stop_price": 130.0,
                }
            ]
        )

    def buy(self, *args, **kwargs) -> TradeResult:
        del args, kwargs
        type(self).buy_calls += 1
        return TradeResult(True, "Compra simulada registrada.", order_id=1)

    def sell(self, *args, **kwargs) -> TradeResult:
        del args, kwargs
        type(self).sell_calls += 1
        return TradeResult(True, "Venta simulada registrada.", order_id=2)

    def review_risk_and_snapshot(self, latest_prices: dict[str, float]) -> RiskReviewResult:
        del latest_prices
        type(self).review_calls += 1
        return RiskReviewResult(True, "Revisión simulada completada.", checked_positions=1)

    def orders(self, limit: int = 50) -> pd.DataFrame:
        del limit
        return pd.DataFrame(
            [
                {
                    "id": 1,
                    "created_at": "2026-07-21T10:00:00+00:00",
                    "side": "BUY",
                    "symbol": "AAPL",
                    "quantity": 10.0,
                    "price": 150.0,
                    "reason": "fixture",
                }
            ]
        )

    def equity_history(self) -> pd.DataFrame:
        return pd.DataFrame([{"created_at": "2026-07-21T10:00:00+00:00", "equity": 101_000.0}])


def _analysis_result() -> AnalysisResult:
    index = pd.bdate_range("2025-01-01", periods=260)
    x = np.arange(len(index), dtype=float)
    prices = pd.DataFrame(
        {
            "AAPL": 150 + x * 0.12 + np.sin(x / 9),
            "MSFT": 300 + x * 0.16 + np.cos(x / 11),
            "NVDA": 100 + x * 0.20 + np.sin(x / 7),
            "SPY": 450 + x * 0.10 + np.cos(x / 13),
        },
        index=index,
    )
    ranking = pd.DataFrame(
        [
            {
                "symbol": symbol,
                "score": score,
                "confidence": 85.0,
                "signal": "COMPRAR",
                "decision": "COMPRAR",
                "price": float(prices[symbol].iloc[-1]),
                "return_3m_pct": 12.0 - position,
                "volatility_pct": 18.0 + position,
                "drawdown_pct": -8.0,
                "trend_factor": 80.0,
                "momentum_factor": 75.0,
                "relative_strength_factor": 70.0,
                "risk_adjusted_factor": 68.0,
                "trend_quality_factor": 77.0,
                "explanation": "Fixture determinista sin red.",
            }
            for position, (symbol, score) in enumerate(
                zip(prices.columns, [82.0, 78.0, 74.0, 70.0], strict=True)
            )
        ]
    )
    errors = {"OFFLINE": "Error parcial simulado"}
    quality = assess_market_data_quality(
        prices,
        [*prices.columns, *errors],
        minimum_history=210,
        provider="Yahoo",
        errors=errors,
        now=prices.index[-1] + pd.Timedelta(days=1),
    )
    return AnalysisResult(
        prices=prices,
        ranking=ranking,
        errors=errors,
        market_regime="Alcista",
        breadth_pct=75.0,
        average_score=76.0,
        quality=quality,
    )


def _fundamental_analysis() -> FundamentalAnalysis:
    snapshot = FundamentalSnapshot(
        symbol="AAPL",
        company_name="Apple Fixture",
        sector="Technology",
        industry="Hardware",
        market_cap=3_000_000_000_000,
        trailing_pe=28.0,
        forward_pe=25.0,
        peg_ratio=1.5,
        price_to_book=12.0,
        enterprise_to_ebitda=20.0,
        return_on_equity=0.40,
        return_on_assets=0.20,
        profit_margin=0.25,
        operating_margin=0.30,
        revenue_growth=0.08,
        earnings_growth=0.10,
        debt_to_equity=1.2,
        current_ratio=1.5,
        free_cash_flow=100_000_000_000,
        operating_cash_flow=120_000_000_000,
        dividend_yield=0.005,
    )
    return FundamentalAnalysis(
        symbol="AAPL",
        score=80.0,
        quality_score=82.0,
        growth_score=75.0,
        valuation_score=70.0,
        balance_sheet_score=78.0,
        cash_flow_score=85.0,
        confidence=95.0,
        decision="COMPRAR",
        explanation="Fixture fundamental sin Yahoo.",
        snapshot=snapshot,
    )


def _market_history() -> pd.DataFrame:
    index = pd.bdate_range("2025-01-01", periods=260)
    close = pd.Series(150 + np.arange(len(index)) * 0.12, index=index)
    return pd.DataFrame(
        {
            "Open": close - 0.4,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": 1_000_000 + np.arange(len(index)) * 1_000,
        },
        index=index,
    )


def _forbid_network(*args, **kwargs):
    del args, kwargs
    raise AssertionError("Las pruebas AppTest no pueden usar Yahoo ni la red.")


@pytest.fixture
def app_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeEngine:
    st.cache_data.clear()
    FakePaperTradingEngine.reset()
    settings = Settings()
    settings.app.version = "1.2.2"
    settings.storage.database_path = str(tmp_path / "history.db")
    settings.paper_trading.database_path = str(tmp_path / "paper.db")
    engine = FakeEngine(settings, _analysis_result())

    monkeypatch.setattr(bootstrap, "build_core_engine", lambda root: engine)
    monkeypatch.setattr(paper_module, "PaperTradingEngine", FakePaperTradingEngine)
    monkeypatch.setattr(market_dashboard, "_load_history", lambda *args: _market_history())
    monkeypatch.setattr(
        fundamental_dashboard,
        "_load_fundamental",
        lambda symbol: _fundamental_analysis(),
    )
    monkeypatch.setattr(
        history_dashboard,
        "read_history",
        lambda path: pd.DataFrame([{"captured_at": "2026-07-21T10:00:00+00:00", "symbol": "AAPL"}]),
    )
    monkeypatch.setattr(yf, "download", _forbid_network)
    monkeypatch.setattr(yf, "Ticker", _forbid_network)
    yield engine
    st.cache_data.clear()


def _assert_no_ui_failure(app: AppTest, context: str) -> None:
    assert not app.exception, (context, [item.message for item in app.exception])
    assert not app.error, (context, [item.value for item in app.error])


def _tab_widget_id(app: AppTest) -> str:
    candidates = [
        widget.id
        for widget in app.session_state.get_widget_states()
        if widget.WhichOneof("value") == "string_value" and widget.string_value in TAB_LABELS
    ]
    assert len(candidates) == 1
    return candidates[0]


def _select_tab(app: AppTest, widget_id: str, label: str) -> None:
    app.session_state[widget_id] = label
    app.run(timeout=APP_TEST_TIMEOUT)
    _assert_no_ui_failure(app, label)


def _button(app: AppTest, label: str):
    matches = [button for button in app.button if button.label == label]
    assert len(matches) == 1, (label, [button.label for button in app.button])
    return matches[0]


def _paper_view_script(paper_engine, latest_prices, selected, settings):
    from elan_ai_invest.dashboard.paper_trading import render_paper_trading_tab

    render_paper_trading_tab(paper_engine, latest_prices, selected, settings)


def _history_view_script(engine, db_path, selected, period):
    from elan_ai_invest.dashboard.history import render_history_tab

    render_history_tab(engine, db_path, selected, period)


def test_app_renders_every_view_and_simulated_actions(app_environment: FakeEngine) -> None:
    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()
    _assert_no_ui_failure(app, "initial")
    assert [tab.label for tab in app.tabs] == list(TAB_LABELS)
    assert app.title[0].value == "ELAN Quantum"
    assert len(app.metric) >= 10
    assert any(item.label == "Calidad global" for item in app.metric)
    assert any("requieren atención" in item.value for item in app.warning)
    assert any(item.label == "Activo principal" for item in app.selectbox)
    assert any(item.label == "Instrumento A" for item in app.selectbox)
    assert any(item.label == "Instrumento B" for item in app.selectbox)

    tab_widget_id = _tab_widget_id(app)
    for label in TAB_LABELS:
        _select_tab(app, tab_widget_id, label)

    calls_before_refresh = len(app_environment.requests)
    _button(app, "Actualizar datos").click().run(timeout=APP_TEST_TIMEOUT)
    assert len(app_environment.requests) > calls_before_refresh
    _assert_no_ui_failure(app, "refresh")


def test_paper_view_executes_only_simulated_actions(app_environment: FakeEngine) -> None:
    latest_prices = {
        symbol: float(series.dropna().iloc[-1])
        for symbol, series in app_environment.result.prices.items()
    }
    app = AppTest.from_function(
        _paper_view_script,
        default_timeout=20,
        args=(
            FakePaperTradingEngine(),
            latest_prices,
            list(latest_prices),
            app_environment.settings,
        ),
    ).run()
    _assert_no_ui_failure(app, "paper initial")

    _button(app, "Comprar en simulador").click().run(timeout=20)
    assert FakePaperTradingEngine.buy_calls == 1
    _button(app, "Vender en simulador").click().run(timeout=20)
    assert FakePaperTradingEngine.sell_calls == 1

    confirmations = [
        checkbox
        for checkbox in app.checkbox
        if checkbox.label.startswith("Confirmo que esta acción")
    ]
    assert len(confirmations) == 1
    confirmations[0].set_value(True)
    _button(app, "Revisar stops y guardar snapshot").click().run(timeout=20)
    assert FakePaperTradingEngine.review_calls == 1
    assert any("Revisión simulada completada" in item.value for item in app.success)


def test_history_view_saves_only_through_fake_engine(app_environment: FakeEngine) -> None:
    app = AppTest.from_function(
        _history_view_script,
        default_timeout=20,
        args=(
            app_environment,
            Path(app_environment.settings.storage.database_path),
            ["AAPL"],
            "2y",
        ),
    ).run()

    _button(app, "Guardar fotografía actual").click().run(timeout=20)

    assert any(request.save_snapshot for request in app_environment.requests)
    assert any("Fotografía guardada" in item.value for item in app.success)


def test_app_searches_and_adds_global_instrument(app_environment: FakeEngine) -> None:
    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()
    search = next(item for item in app.text_input if item.label == "Buscar instrumento")

    search.set_value("EMAAR").run(timeout=APP_TEST_TIMEOUT)
    results = next(item for item in app.selectbox if item.label == "Resultados")
    assert results.value == "EMAAR.DU"

    _button(app, "Añadir seleccionado").click().run(timeout=APP_TEST_TIMEOUT)

    assert "EMAAR.DU" in app.multiselect[0].value
    primary = next(item for item in app.selectbox if item.label == "Activo principal")
    assert primary.value == "EMAAR.DU"
    assert "EMAAR.DU" in app_environment.requests[-1].symbols
    assert not app.exception


def test_app_stops_when_no_asset_is_selected(app_environment: FakeEngine) -> None:
    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()
    app.multiselect[0].set_value([]).run(timeout=APP_TEST_TIMEOUT)

    assert any("Selecciona al menos un activo" in item.value for item in app.warning)
    assert not app.exception


def test_app_contains_startup_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    st.cache_data.clear()
    monkeypatch.setattr(
        bootstrap,
        "build_core_engine",
        lambda root: (_ for _ in ()).throw(RuntimeError("startup fixture")),
    )
    monkeypatch.setattr(yf, "download", _forbid_network)
    monkeypatch.setattr(yf, "Ticker", _forbid_network)

    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()

    assert any("no pudo iniciar" in item.value for item in app.error)
    assert any("Referencia:" in item.value for item in app.error)
    assert not app.exception
    assert all("startup fixture" not in item.value for item in app.error)


def test_app_contains_analysis_failure(app_environment: FakeEngine) -> None:
    st.cache_data.clear()
    app_environment.failure = RuntimeError("analysis fixture")

    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()

    assert any("No se pudo completar" in item.value for item in app.error)
    assert any("Referencia:" in item.value for item in app.error)
    assert not app.exception
    assert all("analysis fixture" not in item.value for item in app.error)


def test_app_stops_on_empty_analysis(app_environment: FakeEngine) -> None:
    st.cache_data.clear()
    app_environment.result = AnalysisResult(
        prices=pd.DataFrame(),
        ranking=pd.DataFrame(),
        errors={"AAPL": "fixture vacío"},
        market_regime="Sin datos",
        breadth_pct=0.0,
        average_score=0.0,
    )

    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()

    assert any("No hay datos suficientes" in item.value for item in app.error)
    assert not app.exception


def test_safe_render_contains_view_failure() -> None:
    app = AppTest.from_string("""
from elan_ai_invest.dashboard.safe import safe_render

def fail():
    raise ValueError("view fixture")

safe_render("Vista de prueba", fail)
""").run()

    assert app.error[0].value.startswith("No se pudo mostrar Vista de prueba. Referencia: `")
    assert re.search(r"[0-9A-F]{12}", app.error[0].value)
    assert "view fixture" not in app.error[0].value
    assert not app.exception
