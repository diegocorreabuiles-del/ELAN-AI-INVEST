from __future__ import annotations

import re
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import streamlit as st
import yfinance as yf
from streamlit.testing.v1 import AppTest

import elan_ai_invest.core.bootstrap as bootstrap
import elan_ai_invest.dashboard.forex as forex_dashboard
import elan_ai_invest.dashboard.fundamental as fundamental_dashboard
import elan_ai_invest.dashboard.history as history_dashboard
import elan_ai_invest.dashboard.market as market_dashboard
import elan_ai_invest.dashboard.news as news_dashboard
import elan_ai_invest.paper_trading as paper_module
from elan_ai_invest.analysis import AssetProfile, AssetType, build_asset_analysis
from elan_ai_invest.core.config import Settings
from elan_ai_invest.core.models import AnalysisRequest, AnalysisResult
from elan_ai_invest.fundamental.models import FundamentalAnalysis, FundamentalSnapshot
from elan_ai_invest.fx import FxHistory, FxPair, FxRoute, FxRouteLeg, FxSourceType, ProviderPair
from elan_ai_invest.market.quality import assess_market_data_quality
from elan_ai_invest.news import (
    CorporateEvent,
    CorporateEventType,
    NewsEventsResult,
    NewsItem,
)
from elan_ai_invest.paper_trading import RiskReviewResult, TradeResult
from elan_ai_invest.storage import load_workspace_symbols, save_workspace_symbols

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"
APP_TEST_TIMEOUT = 60
TAB_LABELS = (
    "Mercado",
    "Inteligencia",
    "Fundamental",
    "Noticias y eventos",
    "Ranking",
    "Riesgo",
    "Cartera",
    "Institucional",
    "Paper Trading",
    "Backtesting",
    "Histórico",
    "Divisas",
    "Sistema",
)


class FakeEngine:
    def __init__(self, settings: Settings, result: AnalysisResult) -> None:
        self.settings = settings
        self.result = result
        self.failure: Exception | None = None
        self.requests: list[AnalysisRequest] = []
        self.news_requests: list[str] = []

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
            "BTC-USD": 60_000 + x * 20 + np.sin(x / 5) * 200,
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
                zip(prices.columns, [82.0, 78.0, 74.0, 70.0, 66.0], strict=True)
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


def _news_events_result(symbol: str = "AAPL") -> NewsEventsResult:
    return NewsEventsResult(
        symbol=symbol,
        news=(
            NewsItem(
                symbol=symbol,
                title="Titular fixture sin red",
                publisher="Fuente fixture",
                url="https://example.com/noticia",
                published_at=datetime(2026, 7, 29, 10, tzinfo=UTC),
                summary="Resumen determinista.",
            ),
        ),
        events=(
            CorporateEvent(
                symbol=symbol,
                event_type=CorporateEventType.EARNINGS,
                event_date=date(2026, 8, 1),
            ),
        ),
        captured_at=datetime(2026, 7, 29, 12, tzinfo=UTC),
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


def _forex_prices() -> pd.DataFrame:
    index = pd.bdate_range("2025-01-01", periods=260)
    x = np.arange(len(index), dtype=float)
    return pd.DataFrame(
        {
            "EUR": 1.08 + x * 0.0002 + np.sin(x / 11) * 0.005,
            "GBP": 1.25 + x * 0.0003 + np.sin(x / 13) * 0.006,
            "JPY": 0.0068 + x * 0.000001 + np.cos(x / 9) * 0.00002,
            "COP": 0.00025 + x * 0.00000001 + np.cos(x / 15) * 0.000001,
        },
        index=index,
    )


def _fx_history(asset_id: str) -> FxHistory:
    pair = FxPair(*asset_id.removeprefix("FX_").split("_"))
    prices = _market_history().copy()
    prices[["Open", "High", "Low", "Close"]] = prices[["Open", "High", "Low", "Close"]].div(100)
    provider_pair = ProviderPair("Test", f"{pair.base}{pair.quote}=X", pair.base, pair.quote)
    route = FxRoute(
        pair,
        FxSourceType.DIRECT,
        (FxRouteLeg(pair.base, pair.quote, provider_pair, False),),
    )
    return FxHistory(
        pair=pair,
        prices=prices,
        route=route,
        coverage_ratio=1.0,
        market_timestamp=pd.Timestamp(prices.index[-1]).tz_localize("UTC"),
        received_at=datetime(2026, 8, 14, 12, tzinfo=UTC),
    )


def test_fx_comparison_normalizes_naive_and_aware_dates() -> None:
    naive = pd.Series(
        [1.0, 2.0],
        index=pd.date_range("2026-01-01", periods=2),
        name="naive",
    )
    aware = pd.Series(
        [3.0, 4.0],
        index=pd.date_range("2026-01-01", periods=2, tz="UTC"),
        name="aware",
    )
    normalized = [
        forex_dashboard._normalize_comparison_series(naive),
        forex_dashboard._normalize_comparison_series(aware),
    ]
    combined = pd.concat(normalized, axis=1)

    assert isinstance(combined.index, pd.DatetimeIndex)
    assert str(combined.index.tz) == "UTC"
    assert combined.notna().all().all()


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
        forex_dashboard,
        "_load_forex_prices",
        lambda *args: (_forex_prices(), ()),
    )
    monkeypatch.setattr(
        forex_dashboard,
        "_load_fx_pair_history",
        lambda asset_id, *args: _fx_history(asset_id),
    )
    monkeypatch.setattr(
        forex_dashboard,
        "_load_comparison_close",
        lambda symbol, *args: _market_history()["Close"].rename(symbol),
    )
    monkeypatch.setattr(
        fundamental_dashboard,
        "_load_fundamental",
        lambda symbol: _fundamental_analysis(),
    )

    def fake_news_loader(symbol: str, max_items: int, cache_bucket: int) -> NewsEventsResult:
        del max_items, cache_bucket
        engine.news_requests.append(symbol)
        return _news_events_result(symbol)

    monkeypatch.setattr(news_dashboard, "_load_news_events", fake_news_loader)
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


def _view_selector(app: AppTest):
    matches = [item for item in app.pills if item.label == "Navegación principal"]
    assert len(matches) == 1
    return matches[0]


def _select_view(app: AppTest, label: str) -> None:
    _view_selector(app).set_value(label).run(timeout=APP_TEST_TIMEOUT)
    _assert_no_ui_failure(app, label)


def _button(app: AppTest, label: str):
    matches = [button for button in app.button if button.label == label]
    assert len(matches) == 1, (label, [button.label for button in app.button])
    return matches[0]


def _multiselect(app: AppTest, label: str):
    return next(item for item in app.multiselect if item.label == label)


def _decision_terminal_script(asset_analysis):
    import pandas as pd

    from elan_ai_invest.dashboard.decision_terminal import render_decision_terminal

    ranking = pd.DataFrame(
        [
            {
                "symbol": asset_analysis.profile.symbol,
                "score": 50.0,
                "signal": "COMPRAR",
            }
        ]
    )
    render_decision_terminal(
        asset_analysis,
        ranking,
        asset_analysis.profile.symbol,
        {asset_analysis.profile.symbol: asset_analysis.profile.name},
    )


def _paper_view_script(paper_engine, latest_prices, selected, settings):
    from elan_ai_invest.dashboard.paper_trading import render_paper_trading_tab

    render_paper_trading_tab(paper_engine, latest_prices, selected, settings)


def _history_view_script(engine, db_path, selected, period):
    from elan_ai_invest.dashboard.history import render_history_tab

    render_history_tab(engine, db_path, selected, period)


def test_app_renders_every_view_and_simulated_actions(app_environment: FakeEngine) -> None:
    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()
    _assert_no_ui_failure(app, "initial")
    assert app_environment.news_requests == []
    navigation = _view_selector(app)
    assert navigation.options == list(TAB_LABELS)
    assert navigation.value == "Mercado"
    assert not app.tabs
    assert app.title[0].value == "ELAN Quantum"
    assert len(app.metric) >= 10
    assert any(item.label == "Calidad global" for item in app.metric)
    assert any(item.label == "Score global" for item in app.metric)
    assert any(item.label == "Convicción" for item in app.metric)
    assert any(item.label == "Decisión" for item in app.metric)
    assert any(item.label == "Confianza datos" for item in app.metric)
    assert not any(item.label == "PER histórico" for item in app.metric)
    assert any("requieren atención" in item.value for item in app.warning)
    assert any(item.label == "Buscar o seleccionar activo" for item in app.selectbox)
    assert any("Procede de tu Universo activo" in item.value for item in app.caption)
    assert any(item.label == "Instrumentos focales" for item in app.multiselect)
    assert any(item.label == "Activo de referencia" for item in app.selectbox)

    for label in TAB_LABELS:
        _select_view(app, label)
    assert app_environment.news_requests == ["AAPL"]

    _select_view(app, "Fundamental")
    assert any(item.label == "PER histórico" and item.value == "28.0x" for item in app.metric)

    _select_view(app, "Divisas")
    assert any(item.label == "Precio actual" for item in app.metric)
    assert any(item.label == "Cobertura" for item in app.metric)
    assert any(item.label == "Divisas con histórico" and item.value == "128" for item in app.metric)
    assert any(item.label == "Pares virtuales" and item.value == "16.256" for item in app.metric)
    assert any("convención BASE/QUOTE" in item.value for item in app.caption)

    calls_before_refresh = len(app_environment.requests)
    _button(app, "Actualizar datos").click().run(timeout=APP_TEST_TIMEOUT)
    assert len(app_environment.requests) > calls_before_refresh
    _assert_no_ui_failure(app, "refresh")


def test_market_chart_horizon_updates_full_analysis_and_history_loader(
    app_environment: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded_periods: list[str] = []

    def load_history(symbol, period, *args):
        del symbol, args
        loaded_periods.append(period)
        return _market_history()

    monkeypatch.setattr(market_dashboard, "_load_history", load_history)
    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()
    horizon = next(item for item in app.selectbox if item.label == "Horizonte del gráfico")

    horizon.set_value("5 años").run(timeout=APP_TEST_TIMEOUT)

    _assert_no_ui_failure(app, "market horizon")
    assert app_environment.requests[-1].period == "5y"
    assert loaded_periods[-1] == "5y"
    global_horizon = next(item for item in app.selectbox if item.label == "Horizonte histórico")
    assert global_horizon.value == "5y"

    horizon = next(item for item in app.selectbox if item.label == "Horizonte del gráfico")
    horizon.set_value("10 años").run(timeout=APP_TEST_TIMEOUT)

    _assert_no_ui_failure(app, "long market horizon")
    assert app_environment.requests[-1].period == "10y"
    assert loaded_periods[-1] == "10y"
    price_scale = next(item for item in app.segmented_control if item.label == "Escala de precio")
    assert price_scale.value == "Logarítmica"


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
            [*latest_prices, "FX_EUR_GBP", "EURUSD=X"],
            app_environment.settings,
        ),
    ).run()
    _assert_no_ui_failure(app, "paper initial")
    buy_selector = next(item for item in app.selectbox if item.label == "Activo a comprar")
    assert "FX_EUR_GBP" not in buy_selector.options
    assert "EURUSD=X" not in buy_selector.options

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


def test_paper_view_with_only_fx_keeps_positions_read_only(
    app_environment: FakeEngine,
) -> None:
    app = AppTest.from_function(
        _paper_view_script,
        default_timeout=20,
        args=(
            FakePaperTradingEngine(),
            {"FX_EUR_GBP": 0.85, "AAPL": 150.0},
            ["FX_EUR_GBP"],
            app_environment.settings,
        ),
    ).run()

    _assert_no_ui_failure(app, "paper FX only")
    assert not any(item.label == "Activo a comprar" for item in app.selectbox)
    assert any("solo lectura" in item.value for item in app.info)


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

    assert "EMAAR.DU" in _multiselect(app, "Universo activo").value
    primary = next(item for item in app.selectbox if item.label == "Buscar o seleccionar activo")
    assert primary.value == "EMAAR.DU"
    assert "EMAAR.DU" in app_environment.requests[-1].symbols
    assert not app.exception


def test_app_searches_virtual_fx_pair(app_environment: FakeEngine) -> None:
    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()
    search = next(item for item in app.text_input if item.label == "Buscar instrumento")

    search.set_value("NGN/XOF").run(timeout=APP_TEST_TIMEOUT)

    results = next(item for item in app.selectbox if item.label == "Resultados")
    assert results.value == "FX_NGN_XOF"
    assert not app.exception


def test_main_cryptoasset_filter_exposes_stablecoins_and_cbdc_scope(
    app_environment: FakeEngine,
) -> None:
    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()
    asset_type = next(item for item in app.selectbox if item.label == "Tipo")

    assert "Criptoactivos (todos)" in asset_type.options
    asset_type.set_value("Cryptoasset").run(timeout=APP_TEST_TIMEOUT)
    search = next(item for item in app.text_input if item.label == "Buscar instrumento")
    search.set_value("USDT").run(timeout=APP_TEST_TIMEOUT)

    results = next(item for item in app.selectbox if item.label == "Resultados")
    assert any(option.startswith("USDT-USD ") for option in results.options)
    search.set_value("USDC").run(timeout=APP_TEST_TIMEOUT)
    results = next(item for item in app.selectbox if item.label == "Resultados")
    assert any(option.startswith("USDC-USD ") for option in results.options)
    search.set_value("CBDC").run(timeout=APP_TEST_TIMEOUT)
    assert any("dinero digital emitido por bancos centrales" in item.value for item in app.caption)
    assert not app.exception


def test_app_main_filters_use_canonical_fx_registry(app_environment: FakeEngine) -> None:
    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()

    asset_type = next(item for item in app.selectbox if item.label == "Tipo")
    asset_type.set_value("Forex").run(timeout=APP_TEST_TIMEOUT)
    country = next(item for item in app.selectbox if item.label == "País")
    country.set_value("NIGERIA").run(timeout=APP_TEST_TIMEOUT)
    market = next(item for item in app.selectbox if item.label == "Bolsa o mercado")
    market.set_value("FX").run(timeout=APP_TEST_TIMEOUT)

    results = next(item for item in app.selectbox if item.label == "Resultados")
    assert results.value == "NGN=X"
    assert not app.exception


def test_workspace_symbols_survive_a_fresh_browser_session(
    app_environment: FakeEngine,
) -> None:
    db_path = Path(app_environment.settings.storage.database_path)
    save_workspace_symbols(db_path, ["MSFT", "NVDA"])

    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()

    assert _multiselect(app, "Universo activo").value == ["MSFT", "NVDA"]
    assert app_environment.requests[-1].symbols == ["MSFT", "NVDA"]

    _multiselect(app, "Universo activo").set_value(["NVDA"]).run(timeout=APP_TEST_TIMEOUT)

    assert load_workspace_symbols(db_path) == ["NVDA"]
    assert not app.exception


def test_persisted_workspace_replaces_stale_session_after_storage_upgrade(
    app_environment: FakeEngine,
) -> None:
    db_path = Path(app_environment.settings.storage.database_path)
    save_workspace_symbols(db_path, ["CIB", "NU"])
    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT)
    app.session_state["workspace_symbols"] = ["SPY"]

    app.run(timeout=APP_TEST_TIMEOUT)

    assert _multiselect(app, "Universo activo").value == ["CIB", "NU"]
    assert app_environment.requests[-1].symbols == ["CIB", "NU"]
    assert not app.exception


def test_default_workspace_is_persisted_on_first_session(
    app_environment: FakeEngine,
) -> None:
    db_path = Path(app_environment.settings.storage.database_path)

    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()

    assert load_workspace_symbols(db_path) == _multiselect(app, "Universo activo").value
    assert not app.exception


def test_active_symbol_stays_synchronized_across_connected_views(
    app_environment: FakeEngine,
) -> None:
    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()
    primary = next(item for item in app.selectbox if item.label == "Buscar o seleccionar activo")

    primary.set_value("MSFT").run(timeout=APP_TEST_TIMEOUT)

    assert app.session_state["active_symbol"] == "MSFT"
    assert not any(item.label == "PER histórico" for item in app.metric)
    active_metric = next(item for item in app.metric if item.label == "Activo")
    assert active_metric.value.startswith("MSFT ·")

    connected_views = {
        "Inteligencia": "Explicación profesional",
        "Fundamental": "Empresa",
        "Noticias y eventos": "Activo para noticias",
        "Ranking": "Detalle",
    }
    for tab_label, selector_label in connected_views.items():
        _select_view(app, tab_label)
        selector = next(item for item in app.selectbox if item.label == selector_label)
        assert selector.value == "MSFT"
        assert app.session_state["active_symbol"] == "MSFT"

    assert app_environment.news_requests == ["MSFT"]


def test_market_comparator_accepts_multiple_instruments(
    app_environment: FakeEngine,
) -> None:
    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()
    comparison = _multiselect(app, "Instrumentos focales")

    comparison.set_value(["AAPL", "MSFT", "BTC-USD"]).run(timeout=APP_TEST_TIMEOUT)

    assert comparison.value == ["AAPL", "MSFT", "BTC-USD"]
    assert any(item.label == "Activo de referencia" for item in app.selectbox)
    assert not any(item.label.startswith("Instrumento focal") for item in app.selectbox)
    assert not app.exception


def test_crypto_asset_skips_stock_pe(
    app_environment: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fundamental_requests: list[str] = []

    def fake_fundamental_loader(symbol: str) -> FundamentalAnalysis:
        fundamental_requests.append(symbol)
        return _fundamental_analysis()

    monkeypatch.setattr(
        fundamental_dashboard,
        "_load_fundamental",
        fake_fundamental_loader,
    )
    st.cache_data.clear()

    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()
    assert fundamental_requests == []
    primary = next(item for item in app.selectbox if item.label == "Buscar o seleccionar activo")

    primary.set_value("BTC-USD").run(timeout=APP_TEST_TIMEOUT)

    assert app.session_state["active_symbol"] == "BTC-USD"
    assert not any(item.label == "PER histórico" for item in app.metric)
    assert fundamental_requests == []


def test_app_stops_when_no_asset_is_selected(app_environment: FakeEngine) -> None:
    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()
    _multiselect(app, "Universo activo").set_value([]).run(timeout=APP_TEST_TIMEOUT)

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


def test_decision_terminal_contains_history_failure(
    app_environment: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_history(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("history fixture")

    monkeypatch.setattr(market_dashboard, "_load_history", fail_history)

    app = AppTest.from_file(APP_PATH, default_timeout=APP_TEST_TIMEOUT).run()

    navigation = _view_selector(app)
    assert navigation.options == list(TAB_LABELS)
    assert navigation.value == "Mercado"
    assert not app.tabs
    assert any("terminal de decisión" in item.value for item in app.error)
    assert any("Referencia:" in item.value for item in app.error)
    assert any(item.label == "Activo" for item in app.metric)
    assert any("Decisión no disponible" in item.value for item in app.info)
    assert all("history fixture" not in item.value for item in app.error)
    assert not app.exception


def test_crypto_terminal_separates_market_derivatives_and_onchain_data() -> None:
    history = _market_history()
    analysis = build_asset_analysis(
        AssetProfile(
            symbol="ETH-USD",
            name="Ethereum",
            asset_type=AssetType.CRYPTO,
        ),
        history,
        benchmark_history=history["Close"] * 0.95,
    )

    app = AppTest.from_function(
        _decision_terminal_script,
        args=(analysis,),
        default_timeout=20,
    ).run()

    _assert_no_ui_failure(app, "crypto terminal")
    assert any(item.value == "Contexto crypto" for item in app.subheader)
    assert any(item.label == "Fuerza vs BTC · 30D" for item in app.metric)
    assert any("Funding: N/D" in item.value for item in app.caption)
    assert any("MVRV: N/D" in item.value for item in app.caption)
    assert not any(item.label == "Fundamental" for item in app.metric)


def test_stablecoin_terminal_uses_peg_language_not_directional_metrics() -> None:
    history = _market_history()
    history["Open"] = 1.0
    history["High"] = 1.002
    history["Low"] = 0.998
    history["Close"] = 1.0
    analysis = build_asset_analysis(
        AssetProfile(
            symbol="USDC-USD",
            name="USD Coin",
            asset_type=AssetType.STABLECOIN,
        ),
        history,
    )

    app = AppTest.from_function(
        _decision_terminal_script,
        args=(analysis,),
        default_timeout=20,
    ).run()

    _assert_no_ui_failure(app, "stablecoin terminal")
    assert any(item.value == "Salud de stablecoin" for item in app.subheader)
    assert any(item.label == "Peg health" for item in app.metric)
    assert any(item.label == "Riesgo de depeg" and item.value == "BAJO" for item in app.metric)
    assert not any(item.label == "Tendencia" for item in app.metric)
    assert not any(item.label == "Fundamental" for item in app.metric)
    assert any("no aplica a stablecoins" in item.value for item in app.info)


def test_stablecoin_terminal_warns_when_observed_depeg_is_critical() -> None:
    history = _market_history()
    history["Open"] = 1.0
    history["High"] = 1.002
    history["Low"] = 0.998
    history["Close"] = 1.0
    history.loc[history.index[-10], "Close"] = 0.94
    analysis = build_asset_analysis(
        AssetProfile(
            symbol="USDC-USD",
            name="USD Coin",
            asset_type=AssetType.STABLECOIN,
        ),
        history,
    )

    app = AppTest.from_function(
        _decision_terminal_script,
        args=(analysis,),
        default_timeout=20,
    ).run()

    _assert_no_ui_failure(app, "critical stablecoin terminal")
    assert any(item.label == "Riesgo de depeg" and item.value == "CRÍTICO" for item in app.metric)
    assert any("riesgo material" in item.value.casefold() for item in app.warning)


def test_meme_terminal_exposes_speculative_warning_and_missing_sources() -> None:
    analysis = build_asset_analysis(
        AssetProfile(
            symbol="DOGE-USD",
            name="Dogecoin",
            asset_type=AssetType.MEME_COIN,
        ),
        _market_history(),
    )

    app = AppTest.from_function(
        _decision_terminal_script,
        args=(analysis,),
        default_timeout=20,
    ).run()

    _assert_no_ui_failure(app, "meme terminal")
    assert any(item.value == "Perfil meme coin" for item in app.subheader)
    assert any("altamente especulativo" in item.value for item in app.warning)
    assert any("Liquidez DEX: N/D" in item.value for item in app.caption)
    assert not any(item.label == "Fundamental" for item in app.metric)


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
