# dashboard/paginas/filiais.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from componentes.kpis import formatar_brl, formatar_pct, formatar_int

def pagina_filiais(df):
    """Aba 2 — Ranking de Filiais + Recuperação de Estoque Crítico."""

    if df.empty:
        st.warning("Nenhum dado para os filtros selecionados.")
        return

    st.subheader("🏪 Ranking de Filiais")

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 1 — Ranking geral por valor parado crítico
    # ─────────────────────────────────────────────────────────────────────────
    df_critico = df[df["critico"] == True]

    ranking = (
        df_critico
        .groupby(["filial_nome", "uf"])
        .agg(
            valor_parado   = ("valor_custo",  "sum"),
            skus_criticos  = ("codigo_sku",   "nunique"),
            dias_medio     = ("dias_estoque", "mean"),
        )
        .reset_index()
        .sort_values("valor_parado", ascending=False)
    )
    ranking["pct_valor"] = (
        ranking["valor_parado"] / ranking["valor_parado"].sum() * 100
    )

    # ── Gráfico de barras horizontal ──────────────────────────────────────────
    col1, col2 = st.columns([3, 2])

    with col1:
        fig = px.bar(
            ranking,
            x="valor_parado",
            y="filial_nome",
            orientation="h",
            color="uf",
            color_discrete_map={"AL": "#e74c3c", "SE": "#f39c12", "BA": "#3498db"},
            labels={"valor_parado": "Valor Parado (R$)", "filial_nome": "Filial"},
            text=ranking["valor_parado"].apply(formatar_brl),
            title="💰 Valor Parado Crítico (+90d) por Filial"
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            height=420, showlegend=True,
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white", yaxis={"categoryorder": "total ascending"}
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**📋 Tabela Resumo**")
        tabela = ranking.copy()
        tabela["Valor Parado"]  = tabela["valor_parado"].apply(formatar_brl)
        tabela["SKUs Críticos"] = tabela["skus_criticos"].apply(formatar_int)
        tabela["Dias Médio"]    = tabela["dias_medio"].apply(lambda x: f"{x:.0f}d")
        tabela["% do Total"]    = tabela["pct_valor"].apply(formatar_pct)
        st.dataframe(
            tabela[["filial_nome", "uf", "Valor Parado",
                     "SKUs Críticos", "Dias Médio", "% do Total"]]
            .rename(columns={"filial_nome": "Filial", "uf": "UF"}),
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 2 — Comparativo por Estado
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("🗺️ Comparativo por Estado")

    por_estado = (
        df_critico
        .groupby("uf")
        .agg(
            valor_parado  = ("valor_custo",  "sum"),
            skus_criticos = ("codigo_sku",   "nunique"),
            filiais       = ("filial_nome",  "nunique"),
        )
        .reset_index()
    )

    col3, col4, col5 = st.columns(3)
    for i, row in por_estado.iterrows():
        col = [col3, col4, col5][i % 3]
        with col:
            st.metric(
                f"🏴 {row['uf']}",
                formatar_brl(row["valor_parado"]),
                delta=f"{formatar_int(row['skus_criticos'])} SKUs críticos",
                delta_color="off"
            )

    fig_estado = px.pie(
        por_estado,
        names="uf",
        values="valor_parado",
        color="uf",
        color_discrete_map={"AL": "#e74c3c", "SE": "#f39c12", "BA": "#3498db"},
        hole=0.45,
        title="Distribuição do Valor Parado por Estado"
    )
    fig_estado.update_layout(
        height=320,
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="white"
    )
    st.plotly_chart(fig_estado, use_container_width=True)

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 3 — Ranking de Recuperação de Estoque Crítico
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("🏆 Ranking de Recuperação — Filiais que Destravaram Estoque Crítico")

    st.info(
        "**Como funciona:** Um SKU é considerado **recuperado** quando estava crítico "
        "(dias_estoque ≥ 90) em uma data anterior e, na data mais recente disponível, "
        "apresenta redução de saldo **ou** atualização na data de última venda. "
        "Quanto maior a redução de valor parado, melhor a posição no ranking."
    )

    datas_unicas = sorted(df["data_arquivo"].dropna().unique())

    if len(datas_unicas) < 2:
        st.warning(
            "⚠️ São necessários dados de pelo menos **2 datas diferentes** "
            "para calcular a recuperação. Continue subindo os CSVs diários!"
        )
    else:
        data_atual   = datas_unicas[-1]
        data_anterior = datas_unicas[-2]

        df_atual = df[df["data_arquivo"] == data_atual]
        df_ant   = df[df["data_arquivo"] == data_anterior]

        # Itens críticos no D-1
        criticos_ant = df_ant[df_ant["critico"] == True][
    ["codigo_sku", "filial_nome", "ultima_venda", "valor_custo", "dias_estoque"]
]

# DEPOIS — defensivo
colunas_desejadas = _safe_cols(
    df_ant,
    ["codigo_sku", "filial_nome", "ultima_venda", "valor_custo", "dias_estoque"]
)
criticos_ant = df_ant[df_ant["critico"] == True][colunas_desejadas]

        # Estado desses itens no dia atual
        estado_atual = df_atual[
            ["filial_key", "codigo_sku", "valor_custo", "saldo",
             "ultima_venda", "filial_nome", "departamento"]
        ].rename(columns={
            "valor_custo": "valor_atual",
            "saldo":       "saldo_atual",
            "ultima_venda":"ultima_venda_atual"
        })

        # JOIN
        comparativo = criticos_ant.merge(
            estado_atual,
            on=["filial_key", "codigo_sku"],
            how="inner"
        )

        # Critério de recuperação:
        # saldo reduziu OU última venda foi atualizada
        comparativo["saldo_reduziu"] = (
            comparativo["saldo_atual"].fillna(0) <
            comparativo["saldo_ant"].fillna(0)
        )
        comparativo["venda_nova"] = (
            comparativo["ultima_venda_atual"].fillna(pd.NaT) >
            comparativo["ultima_venda_ant"].fillna(pd.NaT)
        )
        comparativo["recuperado"] = (
            comparativo["saldo_reduziu"] | comparativo["venda_nova"]
        )
        comparativo["valor_recuperado"] = (
            comparativo["valor_ant"].fillna(0) -
            comparativo["valor_atual"].fillna(0)
        ).clip(lower=0)

        recuperados = comparativo[comparativo["recuperado"] == True]

        if recuperados.empty:
            st.warning("Nenhuma recuperação detectada entre as duas últimas datas.")
        else:
            rank_rec = (
                recuperados
                .groupby(["filial_nome", "departamento"])
                .agg(
                    skus_recuperados  = ("codigo_sku",       "nunique"),
                    valor_recuperado  = ("valor_recuperado", "sum"),
                )
                .reset_index()
                .sort_values("valor_recuperado", ascending=False)
            )
            rank_rec["taxa"] = (
                rank_rec["valor_recuperado"] /
                rank_rec["valor_recuperado"].sum() * 100
            )

            col6, col7 = st.columns([3, 2])

            with col6:
                fig_rec = px.bar(
                    rank_rec,
                    x="valor_recuperado",
                    y="filial_nome",
                    orientation="h",
                    color="departamento",
                    labels={
                        "valor_recuperado": "R$ Recuperado",
                        "filial_nome": "Filial"
                    },
                    text=rank_rec["valor_recuperado"].apply(formatar_brl),
                    title="🏆 Filiais que mais destravaram estoque crítico"
                )
                fig_rec.update_traces(textposition="outside")
                fig_rec.update_layout(
                    height=400,
                    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                    font_color="white",
                    yaxis={"categoryorder": "total ascending"}
                )
                st.plotly_chart(fig_rec, use_container_width=True)

            with col7:
                st.markdown("**📋 Detalhamento**")
                rank_rec["Valor Recuperado"] = rank_rec["valor_recuperado"].apply(
                    formatar_brl
                )
                rank_rec["SKUs Recuperados"] = rank_rec["skus_recuperados"].apply(
                    formatar_int
                )
                rank_rec["Taxa"] = rank_rec["taxa"].apply(formatar_pct)
                st.dataframe(
                    rank_rec[[
                        "filial_nome", "departamento",
                        "SKUs Recuperados", "Valor Recuperado", "Taxa"
                    ]].rename(columns={
                        "filial_nome":   "Filial",
                        "departamento":  "Depto"
                    }),
                    use_container_width=True,
                    hide_index=True
                )

            # ── Detalhe por SKU recuperado ────────────────────────────────────
            with st.expander("🔍 Ver todos os SKUs recuperados (detalhe)"):
                detalhe = recuperados[[
                    "filial_nome", "departamento", "codigo_sku",
                    "saldo_ant", "saldo_atual", "valor_ant",
                    "valor_atual", "valor_recuperado"
                ]].copy()
                detalhe["Saldo Ant."]   = detalhe["saldo_ant"].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) else "-"
                )
                detalhe["Saldo Atual"]  = detalhe["saldo_atual"].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) else "-"
                )
                detalhe["Valor Rec."]   = detalhe["valor_recuperado"].apply(formatar_brl)
                st.dataframe(
                    detalhe[[
                        "filial_nome", "departamento", "codigo_sku",
                        "Saldo Ant.", "Saldo Atual", "Valor Rec."
                    ]].rename(columns={
                        "filial_nome":  "Filial",
                        "departamento": "Depto",
                        "codigo_sku":   "SKU"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
