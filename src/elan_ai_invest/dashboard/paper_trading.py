import plotly.express as px
import streamlit as st


def render_paper_trading_tab(
    paper_engine,
    latest_prices,
    selected,
    settings,
):
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

        buy_symbol = st.selectbox(
            "Activo a comprar",
            selected,
            key="paper_buy_symbol",
        )

        buy_price = latest_prices.get(buy_symbol, 0.0)

        buy_amount = st.number_input(
            "Importe (€)",
            min_value=100.0,
            value=5_000.0,
            step=500.0,
            key="paper_buy_amount",
        )

        st.caption(
            f"Precio usado: {buy_price:,.2f} · "
            f"comisión {settings.paper_trading.commission_pct:.2f}%"
        )

        if st.button(
            "Comprar en simulador",
            type="primary",
            use_container_width=True,
        ):
            result = paper_engine.buy(
                buy_symbol,
                buy_amount,
                buy_price,
                reason="manual_dashboard",
            )

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
                "Activo a vender",
                positions["symbol"].tolist(),
                key="paper_sell_symbol",
            )

            row = positions.loc[
                positions["symbol"] == sell_symbol
            ].iloc[0]

            sell_quantity = st.number_input(
                "Cantidad",
                min_value=0.000001,
                max_value=float(row["quantity"]),
                value=float(row["quantity"]),
                format="%.6f",
                key="paper_sell_quantity",
            )

            st.caption(
                f"Precio usado: {row['current_price']:,.2f} · "
                f"posición: {row['quantity']:.6f}"
            )

            if st.button(
                "Vender en simulador",
                use_container_width=True,
            ):
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
        if st.button(
            "Reiniciar simulador",
            use_container_width=True,
        ):
            paper_engine.reset()
            st.success("Simulador reiniciado.")
            st.rerun()

    with snapshot_col:
        if st.button(
            "Guardar valoración",
            use_container_width=True,
        ):
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
        st.dataframe(
            orders,
            use_container_width=True,
            hide_index=True,
        )