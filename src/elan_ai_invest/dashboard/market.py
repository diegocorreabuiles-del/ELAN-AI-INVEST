import plotly.express as px
import streamlit as st


def render_market_tab(ranking):
    left, right = st.columns([1.2, 0.8])

    with left:
        bubble = px.scatter(
            ranking,
            x="volatility_pct",
            y="score",
            size=ranking["return_3m_pct"].abs().clip(lower=1),
            hover_name="name",
            hover_data=[
                "symbol",
                "signal",
                "confidence",
                "return_3m_pct",
            ],
            labels={
                "volatility_pct": "Volatilidad (%)",
                "score": "Score",
            },
            title="Mapa de oportunidades",
        )

        bubble.add_hline(y=60, line_dash="dash")
        st.plotly_chart(bubble, use_container_width=True)

    with right:
        st.subheader("Top 5")

        for _, row in ranking.head(5).iterrows():
            st.markdown(
                f"**{row['symbol']} · {row['name']}**  \n"
                f"Score **{row['score']:.1f}** · "
                f"3m {row['return_3m_pct']:+.1f}% · "
                f"Vol. {row['volatility_pct']:.1f}%"
            )

            st.progress(int(row["score"]))