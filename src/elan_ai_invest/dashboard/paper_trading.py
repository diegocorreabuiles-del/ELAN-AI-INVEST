from collections.abc import Mapping, Sequence
from typing import Any

import plotly.express as px
import streamlit as st

from elan_ai_invest.fx import is_fx_asset_id


def _is_read_only_fx(symbol: str) -> bool:
    return is_fx_asset_id(symbol) or str(symbol).upper().endswith("=X")


def _render_risk_control(
    paper_engine: Any,
    positions: Any,
    latest_prices: Mapping[str, float],
) -> None:
    st.subheader("Control de riesgo simulado")
    st.caption(
        "Revisión manual con los últimos precios disponibles. No es tiempo real, "
        "no envía órdenes a brokers y no se ejecuta automáticamente."
    )
    if positions.empty:
        st.info("No hay posiciones abiertas. Puedes guardar igualmente un snapshot manual.")
    else:
        watch = positions[["symbol", "current_price", "stop_price"]].copy()
        watch["distancia_stop_pct"] = (watch["current_price"] / watch["stop_price"] - 1.0) * 100.0
        watch = watch.rename(
            columns={
                "symbol": "Activo",
                "current_price": "Precio actual",
                "stop_price": "Stop",
                "distancia_stop_pct": "Distancia al stop (%)",
            }
        )
        st.dataframe(
            watch,
            width="stretch",
            hide_index=True,
            column_config={
                "Precio actual": st.column_config.NumberColumn(format="%.2f"),
                "Stop": st.column_config.NumberColumn(format="%.2f"),
                "Distancia al stop (%)": st.column_config.NumberColumn(format="%+.2f%%"),
            },
        )

    with st.form("paper_risk_review_form", border=True):
        confirmed = st.checkbox("Confirmo que esta acción solo afecta a la cartera simulada")
        submitted = st.form_submit_button(
            "Revisar stops y guardar snapshot",
            type="primary",
            icon=":material/shield:",
            width="stretch",
        )
    if not submitted:
        return
    if not confirmed:
        st.warning("Confirma el alcance simulado antes de ejecutar la revisión.")
        return

    result = paper_engine.review_risk_and_snapshot(latest_prices)
    if not result.success:
        st.error(result.message)
        return
    st.session_state["paper_risk_review_feedback"] = result.message
    st.rerun()


def render_paper_trading_tab(
    paper_engine: Any,
    latest_prices: Mapping[str, float],
    selected: Sequence[str],
    settings: Any,
) -> None:
    st.caption("Solo simulación. No existe conexión con broker ni dinero real.")
    if not settings.paper_trading.enabled or paper_engine is None:
        st.info("Paper trading está desactivado en config/settings.yaml.")
        return
    feedback = st.session_state.pop("paper_risk_review_feedback", None)
    if feedback:
        st.success(feedback)

    tradable = [symbol for symbol in selected if not _is_read_only_fx(symbol)]
    if len(tradable) != len(selected):
        st.info("Las divisas son de solo lectura y no participan en el simulador de órdenes.")

    valuation = paper_engine.valuation(latest_prices)
    cols = st.columns(4)
    cols[0].metric("Patrimonio", f"€{valuation['equity']:,.2f}")
    cols[1].metric("Liquidez", f"€{valuation['cash']:,.2f}")
    cols[2].metric("Posiciones", f"€{valuation['positions_value']:,.2f}")
    cols[3].metric("Rentabilidad", f"{valuation['total_return_pct']:+.2f}%")
    buy_col, sell_col = st.columns(2)
    with buy_col:
        if not tradable:
            st.info("Añade un activo no FX para habilitar compras simuladas.")
        else:
            symbol = st.selectbox("Activo a comprar", tradable, key="paper_buy_symbol")
            amount = st.number_input("Importe (€)", min_value=100.0, value=5000.0, step=500.0)
            if st.button("Comprar en simulador", type="primary", width="stretch"):
                result = paper_engine.buy(
                    symbol, amount, latest_prices.get(symbol, 0.0), reason="manual_dashboard"
                )
                st.success(result.message) if result.success else st.error(result.message)
                if result.success:
                    st.rerun()
    positions = paper_engine.positions(latest_prices)
    with sell_col:
        if positions.empty:
            st.info("No hay posiciones abiertas.")
        else:
            symbol = st.selectbox(
                "Activo a vender", positions["symbol"].tolist(), key="paper_sell_symbol"
            )
            row = positions.loc[positions["symbol"] == symbol].iloc[0]
            quantity = st.number_input(
                "Cantidad",
                min_value=0.000001,
                max_value=float(row["quantity"]),
                value=float(row["quantity"]),
                format="%.6f",
            )
            if st.button("Vender en simulador", width="stretch"):
                result = paper_engine.sell(
                    symbol, quantity, float(row["current_price"]), reason="manual_dashboard"
                )
                st.success(result.message) if result.success else st.error(result.message)
                if result.success:
                    st.rerun()
    positions = paper_engine.positions(latest_prices)
    (
        st.dataframe(positions, width="stretch", hide_index=True)
        if not positions.empty
        else st.info("Cartera simulada vacía.")
    )
    _render_risk_control(paper_engine, positions, latest_prices)

    orders = paper_engine.orders(limit=50)
    with st.expander("Trazabilidad de órdenes simuladas"):
        if orders.empty:
            st.info("Todavía no hay órdenes simuladas.")
        else:
            st.dataframe(orders, width="stretch", hide_index=True)

    history = paper_engine.equity_history()
    if not history.empty:
        st.plotly_chart(
            px.line(history, x="created_at", y="equity", title="Patrimonio simulado"),
            width="stretch",
        )
