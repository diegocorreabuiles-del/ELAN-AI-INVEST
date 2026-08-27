import pandas as pd
import streamlit as st

from elan_ai_invest.backtesting import BacktestEngine
from elan_ai_invest.core.config import BacktestConfig


def render_backtesting_tab(
    prices: pd.DataFrame,
    config: BacktestConfig,
    benchmark_symbol: str,
) -> None:
    engine = BacktestEngine()
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
    try:
        bt = engine.run_momentum(
            prices,
            lookback=lookback,
            top_n=top_n,
            rebalance=rebalance,
            commission_pct=config.commission_pct,
            slippage_pct=config.slippage_pct,
            benchmark_symbol=benchmark_symbol,
        )
    except ValueError as exc:
        st.error(str(exc))
        return
    if bt.empty:
        st.info("No hay datos suficientes para el backtest.")
        return

    stats = engine.performance_stats(bt["strategy"])
    benchmark_stats = engine.performance_stats(bt["benchmark"])
    alpha = stats["total_return_pct"] - benchmark_stats["total_return_pct"]
    total_cost_pct = float(bt["transaction_cost"].sum() * 100)
    with st.container(horizontal=True):
        st.metric("Rentabilidad neta", f"{stats['total_return_pct']:.1f}%", border=True)
        st.metric(
            f"Benchmark {benchmark_symbol}",
            f"{benchmark_stats['total_return_pct']:.1f}%",
            border=True,
        )
        st.metric("Alpha", f"{alpha:.1f}%", border=True)
        st.metric("Sharpe", f"{stats['sharpe']:.2f}", border=True)
        st.metric("Drawdown", f"{stats['max_drawdown_pct']:.1f}%", border=True)
        st.metric("Coste acumulado", f"{total_cost_pct:.2f}%", border=True)

    st.caption(
        f"Supuestos: benchmark {benchmark_symbol}; comisión "
        f"{config.commission_pct:.2f}%; slippage {config.slippage_pct:.2f}%; "
        "costes aplicados al turnover; señales ejecutadas una barra después."
    )
    curves = bt[["strategy", "strategy_gross", "benchmark"]].rename(
        columns={
            "strategy": "Estrategia neta",
            "strategy_gross": "Estrategia bruta",
            "benchmark": f"Benchmark {benchmark_symbol}",
        }
    )
    st.subheader("Evolución base 100")
    st.line_chart(curves * 100)
