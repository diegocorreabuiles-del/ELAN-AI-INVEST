import plotly.express as px
import streamlit as st


def render_paper_trading_tab(paper_engine, latest_prices, selected, settings):
    st.caption("Solo simulación. No existe conexión con broker ni dinero real.")
    valuation = paper_engine.valuation(latest_prices)
    cols = st.columns(4)
    cols[0].metric("Patrimonio", f"€{valuation['equity']:,.2f}")
    cols[1].metric("Liquidez", f"€{valuation['cash']:,.2f}")
    cols[2].metric("Posiciones", f"€{valuation['positions_value']:,.2f}")
    cols[3].metric("Rentabilidad", f"{valuation['total_return_pct']:+.2f}%")
    buy_col, sell_col = st.columns(2)
    with buy_col:
        symbol = st.selectbox("Activo a comprar", selected, key="paper_buy_symbol")
        amount = st.number_input("Importe (€)", min_value=100.0, value=5000.0, step=500.0)
        if st.button("Comprar en simulador", type="primary", use_container_width=True):
            result = paper_engine.buy(symbol, amount, latest_prices.get(symbol, 0.0), reason="manual_dashboard")
            st.success(result.message) if result.success else st.error(result.message)
            if result.success:
                st.rerun()
    positions = paper_engine.positions(latest_prices)
    with sell_col:
        if positions.empty:
            st.info("No hay posiciones abiertas.")
        else:
            symbol = st.selectbox("Activo a vender", positions["symbol"].tolist(), key="paper_sell_symbol")
            row = positions.loc[positions["symbol"] == symbol].iloc[0]
            quantity = st.number_input("Cantidad", min_value=0.000001, max_value=float(row["quantity"]), value=float(row["quantity"]), format="%.6f")
            if st.button("Vender en simulador", use_container_width=True):
                result = paper_engine.sell(symbol, quantity, float(row["current_price"]), reason="manual_dashboard")
                st.success(result.message) if result.success else st.error(result.message)
                if result.success:
                    st.rerun()
    positions = paper_engine.positions(latest_prices)
    st.dataframe(positions, use_container_width=True, hide_index=True) if not positions.empty else st.info("Cartera simulada vacía.")
    history = paper_engine.equity_history()
    if not history.empty:
        st.plotly_chart(px.line(history, x="created_at", y="equity", title="Patrimonio simulado"), use_container_width=True)
