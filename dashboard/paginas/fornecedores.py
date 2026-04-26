# dashboard/paginas/fornecedores.py
import streamlit as st
import pandas as pd
import plotly.express as px
from componentes.kpis import formatar_brl, formatar_int, formatar_pct

def pagina_fornecedores(df):
    """Aba 3 — Ranking de Fornecedores por valor parado crítico."""

    if df.empty:
        st.warning("Nenhum dado para os filtros selecionados.")
        return

    st.subheader("🏭 Ranking de Fornecedores")

    # Verificar se dim_produtos foi carregada (fornecedor preenchido)
    sem_fornecedor = (
        df["fornecedor"].isna() |
        (df["fornecedor"] == "Não informado")
    ).all()

    if sem_fornecedor:
        st.warning(
            "⚠️ **Fornecedor não informado.** "
            "Preencha o arquivo `dados/dimensoes/dim_produtos.csv` com as colunas "
            "`codigo_sku, fornecedor, marca, categoria` para ativar este ranking. "
            "Enquanto isso, o ranking está agrupado por **marca** (se disponível) "
            "ou exibindo todos como 'Não informado'."
        )

    df_critico = df[df["critico"] == True].copy()

    if df_critico.empty:
        st.info("Nenhum item crítico encontrado para os filtros selecionados.")
        return

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 1 — Ranking por fornecedor
    # ─────────────────────────────────────────────────────────────────────────
    col_grupo = "fornecedor"

    ranking_forn = (
        df_critico
        .groupby(col_grupo)
        .agg(
            valor_parado   = ("valor_custo",  "sum"),
            skus_criticos  = ("codigo_sku",   "nunique"),
            filiais_impact = ("filial_nome",  "nunique"),
            dias_medio     = ("dias_estoque", "mean"),
        )
        .reset_index()
        .sort_values("valor_parado", ascending=False)
    )

    col1, col2 = st.columns([3, 2])

    with col1:
        top20 = ranking_forn.head(20)
        fig = px.bar(
            top20,
            x="valor_parado",
            y=col_grupo,
            orientation="h",
            color="filiais_impact",
            color_continuous_scale="Reds",
            labels={
                "valor_parado":    "Valor Parado (R$)",
                col_grupo:         "Fornecedor",
                "filiais_impact":  "Filiais"
            },
            text=top20["valor_parado"].apply(formatar_brl),
            title="Top 20 Fornecedores — Valor Parado Crítico (+90d)"
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            height=500, showlegend=False,
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white",
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=True
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**📋 Tabela Completa**")
        tabela = ranking_forn.copy()
        tabela["Valor Parado"]   = tabela["valor_parado"].apply(formatar_brl)
        tabela["SKUs Críticos"]  = tabela["skus_criticos"].apply(formatar_int)
        tabela["Filiais Impact."]= tabela["filiais_impact"].apply(formatar_int)
        tabela["Dias Médio"]     = tabela["dias_medio"].apply(lambda x: f"{x:.0f}d")
        st.dataframe(
            tabela[[
                col_grupo, "Valor Parado",
                "SKUs Críticos", "Filiais Impact.", "Dias Médio"
            ]].rename(columns={col_grupo: "Fornecedor"}),
            use_container_width=True,
            hide_index=True,
            height=480
        )

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 2 — Detalhamento por fornecedor selecionado
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("🔍 Detalhamento por Fornecedor")

    fornecedores_lista = ["Selecione..."] + sorted(
        df_critico[col_grupo].dropna().unique().tolist()
    )
    forn_sel = st.selectbox("Escolha um fornecedor:", fornecedores_lista)

    if forn_sel != "Selecione...":
        df_forn = df_critico[df_critico[col_grupo] == forn_sel]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Valor Parado",    formatar_brl(df_forn["valor_custo"].sum()))
        m2.metric("SKUs Críticos",   formatar_int(df_forn["codigo_sku"].nunique()))
        m3.metric("Filiais Impact.", formatar_int(df_forn["filial_nome"].nunique()))
        m4.metric("Dias Médio",      f"{df_forn['dias_estoque'].mean():.0f}d")

        col3, col4 = st.columns(2)

        with col3:
            # Por filial
            por_filial = (
                df_forn.groupby("filial_nome")
                .agg(valor=("valor_custo", "sum"), skus=("codigo_sku", "nunique"))
                .reset_index()
                .sort_values("valor", ascending=False)
            )
            fig2 = px.bar(
                por_filial, x="filial_nome", y="valor",
                color="valor", color_continuous_scale="Oranges",
                labels={"filial_nome": "Filial", "valor": "R$"},
                text=por_filial["valor"].apply(formatar_brl),
                title=f"Valor Parado por Filial — {forn_sel}"
            )
            fig2.update_traces(textposition="outside")
            fig2.update_layout(
                height=320, showlegend=False,
                plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                font_color="white", coloraxis_showscale=False
            )
            st.plotly_chart(fig2, use_container_width=True)

        with col4:
            # Por departamento
            por_depto = (
                df_forn.groupby("departamento")
                .agg(valor=("valor_custo", "sum"), skus=("codigo_sku", "nunique"))
                .reset_index()
                .sort_values("valor", ascending=False)
            )
            fig3 = px.pie(
                por_depto, names="departamento", values="valor",
                hole=0.4,
                title=f"Distribuição por Departamento — {forn_sel}"
            )
            fig3.update_layout(
                height=320,
                plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                font_color="white"
            )
            st.plotly_chart(fig3, use_container_width=True)

        # Tabela de SKUs do fornecedor
        with st.expander(f"📦 Ver todos os SKUs críticos de {forn_sel}"):
            tabela_sku = df_forn[[
                "filial_nome", "departamento", "codigo_sku", "descricao",
                "saldo", "dias_estoque", "ultima_venda", "valor_custo"
            ]].copy()
            tabela_sku["valor_custo"] = tabela_sku["valor_custo"].apply(formatar_brl)
            tabela_sku["dias_estoque"] = tabela_sku["dias_estoque"].apply(
                lambda x: f"{x:.0f}d" if pd.notna(x) else "-"
            )
            st.dataframe(
                tabela_sku.rename(columns={
                    "filial_nome":   "Filial",
                    "departamento":  "Depto",
                    "codigo_sku":    "SKU",
                    "descricao":     "Descrição",
                    "saldo":         "Saldo",
                    "dias_estoque":  "Dias",
                    "ultima_venda":  "Últ. Venda",
                    "valor_custo":   "Valor Parado"
                }),
                use_container_width=True,
                hide_index=True
            )

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 3 — Tendência (se houver histórico)
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("📈 Tendência dos Top 5 Fornecedores")

    top5_forn = ranking_forn.head(5)[col_grupo].tolist()
    df_tend = df[
        (df["critico"] == True) &
        (df[col_grupo].isin(top5_forn))
    ].groupby(["data_arquivo", col_grupo]).agg(
        valor=("valor_custo", "sum")
    ).reset_index()

    if df_tend["data_arquivo"].nunique() < 2:
        st.info("Acumule mais dias de dados para ver a tendência.")
    else:
        fig_tend = px.line(
            df_tend,
            x="data_arquivo", y="valor",
            color=col_grupo,
            markers=True,
            labels={
                "data_arquivo": "Data",
                "valor":        "Valor Parado (R$)",
                col_grupo:      "Fornecedor"
            },
            title="Evolução do Valor Parado — Top 5 Fornecedores"
        )
        fig_tend.update_layout(
            height=380,
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white"
        )
        st.plotly_chart(fig_tend, use_container_width=True)
