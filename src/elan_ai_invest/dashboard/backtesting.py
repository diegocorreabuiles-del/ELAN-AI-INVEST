import plotly.express as px
import streamlit as st

from elan_ai_invest.backtesting import momentum_backtest, performance_stats
from elan_ai_invest.core.config import BacktestConfig


def render_backtesting_tab(prices, config: BacktestConfig):
    a, b, c = st.columns(3)
    lookback_options = sorted({21, 63, 126, config.lookback})
    lookback = a.selectbox(
        "Momentum", lookback_options, index=lookback_options.index(config.lookback)
    )
    maximum_assets = max(1, min(config.top_n, len(prices.columns)))
    top_n = b.slider("Número de activos", 1, len(prices.columns), maximum_assets)
    rebalance_options = sorted({5, 21, 63, config.rebalance_days})
    rebalance = c.selectbox(
        "Rebalanceo",
        rebalance_options,
        index=rebalance_options.index(config.rebalance_days),
    )
    bt = momentum_backtest(prices, lookback=lookback, top_n=top_n, rebalance=rebalance)
    if bt.empty:
        st.info("No hay datos suficientes para el backtest.")
        return
    stats = performance_stats(bt["strategy"])
    cols = st.columns(4)
    cols[0].metric("Rentabilidad", f"{stats['total_return_pct']:.1f}%")
    cols[1].metric("CAGR", f"{stats['cagr_pct']:.1f}%")
    cols[2].metric("Sharpe", f"{stats['sharpe']:.2f}")
    cols[3].metric("Drawdown", f"{stats['max_drawdown_pct']:.1f}%")
    st.plotly_chart(px.line(bt * 100, title="Backtesting"), width="stretch")
