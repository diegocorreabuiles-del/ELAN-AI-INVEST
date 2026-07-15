from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from elan_ai_invest.backtest import momentum_backtest, performance_stats
from elan_ai_invest.core.bootstrap import build_core_engine
from elan_ai_invest.core.models import AnalysisRequest
from elan_ai_invest.paper_trading import PaperTradingEngine
from elan_ai_invest.portfolio import build_portfolio, portfolio_equity_curve
from elan_ai_invest.risk import calculate_risk_report, suggested_position_size_pct
from elan_ai_invest.storage import read_history
from elan_ai_invest.system_status import collect_system_status

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="ELAN Quantum", page_icon="📈", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
[data-testid="stMetricValue"] {font-size: 1.75rem;}
</style>
""",
    unsafe_allow_html=True,
)

ENGINE = build_core_engine(ROOT)
DB_PATH = ROOT / ENGINE.settings.storage.database_path
watchlist = pd.read_csv(ROOT / "config" / "watchlist.csv")
name_map = dict(zip(watchlist["symbol"], watchlist["name"], strict=True))

st.title("ELAN Quantum")
st.caption("AI Investment Platform · v0.7 Foundation · simulación, no asesoramiento financiero")

with st.sidebar:
    st.header("Configuración")
    selected = st.multiselect(
        "Activos",
        options=watchlist["symbol"].tolist(),
        default=watchlist["symbol"].tolist(),
    )
    period = st.selectbox("Historial", ["1y", "2y", "5y"], index=1)
    capital = st.number_input(
        "Capital simulado (€)", min_value=1_000.0, value=100_000.0, step=5_000.0
    )
    refresh = st.button("Actualizar mercado", type="primary", use_container_width=True)

if not selected:
    st.warning("Selecciona al menos un activo.")
    st.stop()


@st.cache_data(ttl=3600, show_spinner=False)
def run_analysis(symbols: tuple[str, ...], selected_period: str):
    return ENGINE.run_analysis(AnalysisRequest(symbols=list(symbols), period=selected_period))


if refresh:
    run_analysis.clear()

with st.spinner("ELAN analiza mercado y riesgo..."):
    analysis = run_analysis(tuple(selected), period)

prices = analysis.prices
ranking = analysis.ranking.copy()
if prices.empty or ranking.empty:
    st.error("No hay datos suficientes.")
    st.stop()
ranking["name"] = ranking["symbol"].map(name_map).fillna(ranking["symbol"])

paper_engine = PaperTradingEngine(
    ROOT / ENGINE.settings.paper_trading.database_path,
    initial_capital=ENGINE.settings.paper_trading.initial_capital,
    commission_pct=ENGINE.settings.paper_trading.commission_pct,
    stop_loss_pct=ENGINE.settings.paper_trading.stop_loss_pct,
    max_open_positions=ENGINE.settings.paper_trading.max_open_positions,
)
latest_prices = {
    symbol: float(prices[symbol].dropna().iloc[-1])
    for symbol in prices.columns
    if not prices[symbol].dropna().empty
}

risk_report = calculate_risk_report(
    prices,
    annualisation_days=ENGINE.settings.risk.annualisation_days,
)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Régimen", analysis.market_regime)
m2.metric("Score medio", f"{analysis.average_score:.1f}/100")
m3.metric("Riesgo cartera", risk_report.risk_level)
m4.metric("Volatilidad", f"{risk_report.annual_volatility_pct:.1f}%")
m5.metric(
    "VaR 95% diario",
    f"{risk_report.var_95_pct:.2f}%",
    f"€{capital * risk_report.var_95_pct / 100:,.0f}",
)

(
    tab_market,
    tab_ranking,
    tab_risk,
    tab_portfolio,
    tab_paper,
    tab_backtest,
    tab_history,
    tab_system,
) = st.tabs(
    [
        "Mercado",
        "Ranking",
        "Riesgo",
        "Cartera",
        "Paper Trading",
        "Backtesting",
        "Histórico",
        "Sistema",
    ]
)

with tab_market:
    left, right = st.columns([1.2, 0.8])
    with left:
        bubble = px.scatter(
            ranking,
            x="volatility_pct",
            y="score",
            size=ranking["return_3m_pct"].abs().clip(lower=1),
            hover_name="name",
            hover_data=["symbol", "signal", "confidence", "return_3m_pct"],
            labels={"volatility_pct": "Volatilidad (%)", "score": "Score"},
            title="Mapa de oportunidades",
        )
        bubble.add_hline(y=60, line_dash="dash")
        st.plotly_chart(bubble, use_container_width=True)
    with right:
        st.subheader("Top 5")
        for _, row in ranking.head(5).iterrows():
            st.markdown(
                f"**{row['symbol']} · {row['name']}**  \n"
                f"Score **{row['score']:.1f}** · 3m {row['return_3m_pct']:+.1f}% · "
                f"Vol. {row['volatility_pct']:.1f}%"
            )
            st.progress(int(row["score"]))

with tab_ranking:
    st.dataframe(
        ranking[
            [
                "symbol",
                "name",
                "score",
                "confidence",
                "signal",
                "price",
                "return_3m_pct",
                "volatility_pct",
                "drawdown_pct",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
    chosen = st.selectbox("Detalle", ranking["symbol"].tolist())
    series = prices[chosen].dropna()
    chart = go.Figure()
    chart.add_trace(go.Scatter(x=series.index, y=series, name="Precio"))
    chart.add_trace(go.Scatter(x=series.index, y=series.rolling(50).mean(), name="MM50"))
    chart.add_trace(go.Scatter(x=series.index, y=series.rolling(200).mean(), name="MM200"))
    st.plotly_chart(chart, use_container_width=True)

with tab_risk:
    st.subheader("Risk Engine")
    r1, r2, r3, r4, r5 = st.columns(5)
    r1.metric("VaR 95%", f"{risk_report.var_95_pct:.2f}%")
    r2.metric("CVaR 95%", f"{risk_report.cvar_95_pct:.2f}%")
    r3.metric("VaR 99%", f"{risk_report.var_99_pct:.2f}%")
    r4.metric("Drawdown máximo", f"{risk_report.max_drawdown_pct:.1f}%")
    r5.metric("Diversificación", f"{risk_report.diversification_ratio:.2f}x")

    st.caption("VaR/CVaR históricos diarios. La cartera simulada usa pesos iguales.")
    risk_table = risk_report.asset_risk.merge(ranking[["symbol", "score"]], on="symbol", how="left")
    risk_table["suggested_position_pct"] = risk_table["volatility_pct"].apply(
        lambda value: suggested_position_size_pct(
            value,
            risk_budget_pct=ENGINE.settings.risk.risk_budget_per_position_pct,
            max_position_pct=ENGINE.settings.risk.max_position_pct,
        )
    )
    risk_table["suggested_amount_eur"] = risk_table["suggested_position_pct"] / 100 * capital
    st.dataframe(risk_table, use_container_width=True, hide_index=True)

    st.subheader("Correlaciones")
    heatmap = px.imshow(
        risk_report.correlation,
        text_auto=".2f",
        zmin=-1,
        zmax=1,
        aspect="auto",
    )
    st.plotly_chart(heatmap, use_container_width=True)

    st.subheader("Contribución al riesgo")
    contribution = px.bar(
        risk_table,
        x="symbol",
        y="risk_contribution_pct",
        labels={"risk_contribution_pct": "% riesgo", "symbol": "Activo"},
    )
    st.plotly_chart(contribution, use_container_width=True)


with tab_portfolio:
    st.subheader("Portfolio Engine")
    profile = st.selectbox("Perfil", ["conservador", "moderado", "agresivo"], index=1)
    plan = build_portfolio(
        ranking,
        risk_report.asset_risk,
        capital=capital,
        profile=profile,
        min_score=55.0,
        max_positions=8,
        max_position_pct=ENGINE.settings.risk.max_position_pct,
        min_cash_pct=20.0,
    )
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Capital", f"€{capital:,.0f}")
    p2.metric("Invertido", f"{plan.invested_weight_pct:.1f}%")
    p3.metric("Liquidez", f"{plan.cash_weight_pct:.1f}%")
    p4.metric("Riesgo estimado", plan.risk_level)

    if plan.allocations.empty:
        st.info("No hay activos con score suficiente. ELAN mantiene liquidez.")
    else:
        st.dataframe(plan.allocations, use_container_width=True, hide_index=True)
        pie_data = plan.allocations[["symbol", "weight_pct"]].copy()
        pie_data.loc[len(pie_data)] = ["CASH", plan.cash_weight_pct]
        st.plotly_chart(
            px.pie(pie_data, names="symbol", values="weight_pct", title="Distribución propuesta"),
            use_container_width=True,
        )
        curve = portfolio_equity_curve(prices, plan.allocations, capital)
        if not curve.empty:
            st.plotly_chart(
                px.line(curve, title="Cartera simulada vs SPY"),
                use_container_width=True,
            )

with tab_paper:
    st.subheader("Paper Trading Engine")
    st.caption("Solo simulación. No existe conexión con broker ni dinero real.")

    stop_results = paper_engine.apply_stop_losses(latest_prices)
    for result in stop_results:
        if result.success:
            st.warning(result.message + " por stop-loss")

    valuation = paper_engine.valuation(latest_prices)
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Patrimonio", f"€{valuation['equity']:,.2f}")
    t2.metric("Liquidez", f"€{valuation['cash']:,.2f}")
    t3.metric("Posiciones", f"€{valuation['positions_value']:,.2f}")
    t4.metric("Rentabilidad", f"{valuation['total_return_pct']:+.2f}%")

    buy_col, sell_col = st.columns(2)
    with buy_col:
        st.markdown("#### Compra simulada")
        buy_symbol = st.selectbox("Activo a comprar", selected, key="paper_buy_symbol")
        buy_price = latest_prices.get(buy_symbol, 0.0)
        buy_amount = st.number_input(
            "Importe (€)", min_value=100.0, value=5_000.0, step=500.0, key="paper_buy_amount"
        )
        st.caption(
            f"Precio usado: {buy_price:,.2f} · comisión {ENGINE.settings.paper_trading.commission_pct:.2f}%"
        )
        if st.button("Comprar en simulador", type="primary", use_container_width=True):
            result = paper_engine.buy(buy_symbol, buy_amount, buy_price, reason="manual_dashboard")
            if result.success:
                st.success(result.message)
                st.rerun()
            else:
                st.error(result.message)

    positions = paper_engine.positions(latest_prices)
    with sell_col:
        st.markdown("#### Venta simulada")
        if positions.empty:
            st.info("No hay posiciones abiertas.")
        else:
            sell_symbol = st.selectbox(
                "Activo a vender", positions["symbol"].tolist(), key="paper_sell_symbol"
            )
            row = positions.loc[positions["symbol"] == sell_symbol].iloc[0]
            sell_quantity = st.number_input(
                "Cantidad",
                min_value=0.000001,
                max_value=float(row["quantity"]),
                value=float(row["quantity"]),
                format="%.6f",
                key="paper_sell_quantity",
            )
            st.caption(
                f"Precio usado: {row['current_price']:,.2f} · posición: {row['quantity']:.6f}"
            )
            if st.button("Vender en simulador", use_container_width=True):
                result = paper_engine.sell(
                    sell_symbol,
                    sell_quantity,
                    float(row["current_price"]),
                    reason="manual_dashboard",
                )
                if result.success:
                    st.success(result.message)
                    st.rerun()
                else:
                    st.error(result.message)

    st.markdown("#### Posiciones abiertas")
    positions = paper_engine.positions(latest_prices)
    if positions.empty:
        st.info("Cartera simulada vacía.")
    else:
        st.dataframe(
            positions[
                [
                    "symbol",
                    "quantity",
                    "average_price",
                    "current_price",
                    "stop_price",
                    "market_value",
                    "unrealised_pnl",
                    "return_pct",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

    controls, snapshot_col = st.columns(2)
    with controls:
        if st.button("Reiniciar simulador", use_container_width=True):
            paper_engine.reset()
            st.success("Simulador reiniciado.")
            st.rerun()
    with snapshot_col:
        if st.button("Guardar valoración", use_container_width=True):
            paper_engine.save_snapshot(latest_prices)
            st.success("Valoración guardada.")

    history_equity = paper_engine.equity_history()
    if not history_equity.empty:
        st.plotly_chart(
            px.line(
                history_equity,
                x="created_at",
                y="equity",
                title="Evolución del patrimonio simulado",
            ),
            use_container_width=True,
        )

    st.markdown("#### Operaciones")
    orders = paper_engine.orders()
    if orders.empty:
        st.info("Sin operaciones todavía.")
    else:
        st.dataframe(orders, use_container_width=True, hide_index=True)


with tab_backtest:
    a, b, c = st.columns(3)
    lookback = a.selectbox("Momentum", [21, 63, 126], index=1)
    top_n = b.slider(
        "Número de activos", 1, min(8, len(prices.columns)), min(3, len(prices.columns))
    )
    rebalance = c.selectbox("Rebalanceo", [5, 21, 63], index=1)
    bt = momentum_backtest(prices, lookback=lookback, top_n=top_n, rebalance=rebalance)
    if not bt.empty:
        stats = performance_stats(bt["strategy"])
        cols = st.columns(4)
        cols[0].metric("Rentabilidad", f"{stats['total_return_pct']:.1f}%")
        cols[1].metric("CAGR", f"{stats['cagr_pct']:.1f}%")
        cols[2].metric("Sharpe", f"{stats['sharpe']:.2f}")
        cols[3].metric("Drawdown", f"{stats['max_drawdown_pct']:.1f}%")
        st.plotly_chart(px.line(bt * 100), use_container_width=True)

with tab_history:
    if st.button("Guardar fotografía actual"):
        ENGINE.run_analysis(
            AnalysisRequest(symbols=list(selected), period=period, save_snapshot=True)
        )
        st.success("Fotografía guardada.")
    history = read_history(DB_PATH)
    if history.empty:
        st.info("Sin histórico todavía.")
    else:
        st.dataframe(history, use_container_width=True, hide_index=True)

with tab_system:
    st.subheader("Estado del sistema")
    status = collect_system_status(ROOT, ENGINE.settings)
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Versión", status.version)
    s2.metric("Python", status.python_version)
    s3.metric("Proveedor", status.market_provider)
    s4.metric("Entorno", status.environment)
    st.dataframe(status.as_dataframe(), use_container_width=True, hide_index=True)
    if status.ok:
        st.success("Sistema listo.")
    else:
        st.warning("Hay comprobaciones pendientes. Ejecuta update.bat.")

if analysis.errors:
    with st.expander("Errores de descarga"):
        st.json(analysis.errors)
