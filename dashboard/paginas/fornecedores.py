# dashboard/paginas/fornecedores.py
import streamlit as st
import pandas as pd
import plotly.express as px
from componentes.kpis import formatar_brl, formatar_int

def pagina_fornecedores(df):
    st.subheader("🏭 Análise por Fornecedor")

    # ── Verificar se coluna existe ────────────────────────────────────────────
    if "fornecedor" not in df.columns:
        st.info(
            "ℹ️ A coluna **fornecedor** não está presente nos CSVs carregados. "
            "Esta aba ficará disponível quando os arquivos incluírem essa informação."
        )
        return

    if df.empty:
        st.warning("Nenhum dado para os filtros selecionados.")
        return

    # Tratar fornecedor vazio
    df = df.copy()
    df["fornecedor"] = df["fornecedor"].fillna("(sem fornecedor)").str.strip()
    df.loc[df["fornecedor"] == "", "fornecedor"] = "(sem fornecedor)"

    # ── Ranking por valor parado ──────────────────────────────────────────────
    df_forn = df[df["critico"] == True].groupby("fornecedor").agg(
        valor_parado  = ("valor_custo",   "sum"),
        skus_criticos = ("codigo_sku",    "nunique"),
        dias_medio    = ("dias_estoque",  "mean"),
    ).reset_index().sort_values("valor_parado", ascending=False)

    df_forn["valor_fmt"] = df_forn["valor_parado"].apply(formatar_brl)
    df_forn["dias_fmt"]  = df_forn["dias_medio"].apply(lambda x: f"{x:.0f} dias")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🔴 Top Fornecedores — Valor Parado**")
        fig = px.bar(
            df_forn.head(15),
            x="valor_parado", y="fornecedor",
            orientation="h",
            color="valor_parado",
            color_continuous_scale="Reds",
            text="valor_fmt",
            labels={"valor_parado": "R$", "fornecedor": "Fornecedor"}
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            showlegend=False, height=450,
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white", coloraxis_showscale=False,
            yaxis=dict(autorange="reversed")
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**📋 Tabela Completa**")
        st.dataframe(
            df_forn[["fornecedor", "skus_criticos", "dias_fmt", "valor_fmt"]].rename(columns={
                "fornecedor":    "Fornecedor",
                "skus_criticos": "SKUs Críticos",
                "dias_fmt":      "Dias Médio",
                "valor_fmt":     "Valor Parado"
            }),
            use_container_width=True,
            hide_index=True
        )
