import pandas as pd

from elan_ai_invest.portfolio import build_portfolio, portfolio_equity_curve


def test_build_portfolio_moderate_respects_limits():
    ranking = pd.DataFrame(
        {
            "symbol": ["AAA", "BBB", "CCC"],
            "score": [90.0, 80.0, 70.0],
            "confidence": [85.0, 75.0, 65.0],
            "signal": ["Fuerte", "Positivo", "Positivo"],
        }
    )
    risk = pd.DataFrame(
        {
            "symbol": ["AAA", "BBB", "CCC"],
            "volatility_pct": [20.0, 15.0, 10.0],
            "risk_contribution_pct": [40.0, 35.0, 25.0],
        }
    )
    plan = build_portfolio(ranking, risk, capital=100_000, profile="moderado")
    assert plan.invested_weight_pct <= 80.0001
    assert plan.cash_weight_pct >= 19.9999
    assert plan.allocations["weight_pct"].max() <= 15.0001
    assert abs(plan.allocations["amount_eur"].sum() - 100_000 * plan.invested_weight_pct / 100) < 0.01


def test_portfolio_equity_curve_returns_data():
    dates = pd.date_range("2025-01-01", periods=100, freq="D")
    prices = pd.DataFrame({"AAA": range(100, 200), "SPY": range(200, 300)}, index=dates)
    allocations = pd.DataFrame({"symbol": ["AAA"], "weight_pct": [50.0]})
    curve = portfolio_equity_curve(prices, allocations, 100_000)
    assert not curve.empty
    assert "portfolio" in curve.columns
