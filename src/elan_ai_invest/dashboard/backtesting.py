import plotly.express as px
import streamlit as st

from elan_ai_invest.backtest import momentum_backtest, performance_stats


def render_backtesting_tab(prices):
    a, b, c = st.columns(3)

    lookback = a.selectbox(
        "Momentum",
        [21, 63, 126],
        index=1,
        key="backtest_lookback",
    )

    top_n = b.slider(
        "Número de activos",
        1,
        min(8, len(prices.columns)),
        min(3, len(prices.columns)),
        key="backtest_top_n",
    )

    rebalance = c.selectbox(
        "Rebalanceo",
        [5, 21, 63],
        index=1,
        key="backtest_rebalance",
    )

    bt = momentum_backtest(
        prices,
        lookback=lookback,
        top_n=top_n,
        rebalance=rebalance,
    )

    if bt.empty:
        st.info("No hay datos suficientes para el backtest.")
        return

    stats = performance_stats(bt["strategy"])

    cols = st.columns(4)
    cols[0].metric("Rentabilidad", f"{stats['total_return_pct']:.1f}%")
    cols[1].metric("CAGR", f"{stats['cagr_pct']:.1f}%")
    cols[2].metric("Sharpe", f"{stats['sharpe']:.2f}")
    cols[3].metric("Drawdown", f"{stats['max_drawdown_pct']:.1f}%")

    st.plotly_chart(
        px.line(bt * 100, title="Backtesting"),
        use_container_width=True,
    )