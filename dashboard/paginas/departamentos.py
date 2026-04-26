# dashboard/paginas/departamentos.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from componentes.kpis import formatar_brl, formatar_int, formatar_pct

def pagina_departamentos(df):
    """Aba 4 — Ranking de Departamentos + Heatmap Depto × Filial."""

    if df.empty:
        st.warning("Nenhum dado para os filtros selecionados.")
        return

    st.subheader("📂 Ranking por Departamento")

    df_critico = df[df["critico"] == True]

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 1 — KPIs por departamento
    # ─────────────────────────────────────────────────────────────────────────
    ranking_dep = (
        df.groupby("departamento")
        .agg(
            total_skus     = ("codigo_sku",   "nunique"),
            skus_criticos  = ("critico",      "sum"),
            valor_total    = ("valor_custo",  "sum"),
            valor_parado   = ("valor_custo",  lambda x: x[df.loc[x.index, "critico"]].sum()),
            dias_medio     = ("dias_estoque", "mean"),
        )
        .reset_index()
    )
    ranking_dep["pct_skus_criticos"] = (
        ranking_dep["skus_criticos"] / ranking_dep["total_skus"] * 100
    )
    ranking_dep["pct_valor_parado"] = (
        ranking_dep["valor_parado"] / ranking_dep["valor_total"] * 100
    )
    ranking_dep = ranking_dep.sort_values("valor_parado", ascending=False)

    # Cards por departamento
    cols = st.columns(len(ranking_dep))
    for i, (_, row) in enumerate(ranking_dep.iterrows()):
        with cols[i]:
            st.metric(
                f"📂 {row['departamento']}",
                formatar_brl(row["valor_parado"]),
                delta=f"{formatar_pct(row['pct_skus_criticos'])} críticos",
                delta_color="off"
            )

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 2 — Gráficos comparativos
    # ─────────────────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        fig1 = px.bar(
            ranking_dep,
            x="departamento",
            y="valor_parado",
            color="pct_skus_criticos",
            color_continuous_scale="Reds",
            labels={
                "departamento":       "Departamento",
                "valor_parado":       "Valor Parado (R$)",
                "pct_skus_criticos":  "% SKUs Críticos"
            },
            text=ranking_dep["valor_parado"].apply(formatar_brl),
            title="💰 Valor Parado por Departamento"
        )
        fig1.update_traces(textposition="outside")
        fig1.update_layout(
            height=380, showlegend=False,
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white", coloraxis_showscale=True
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = px.bar(
            ranking_dep,
            x="departamento",
            y="pct_skus_criticos",
            color="departamento",
            labels={
                "departamento":      "Departamento",
                "pct_skus_criticos": "% SKUs Críticos"
            },
            text=ranking_dep["pct_skus_criticos"].apply(
                lambda x: f"{x:.1f}%"
            ),
            title="⚠️ % de SKUs Críticos por Departamento"
        )
        fig2.update_traces(textposition="outside")
        fig2.update_layout(
            height=380, showlegend=False,
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white"
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 3 — Heatmap Departamento × Filial
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("🌡️ Heatmap — Valor Parado: Departamento × Filial")

    opcao_heatmap = st.radio(
        "Métrica do heatmap:",
        ["Valor Parado (R$)", "% SKUs Críticos", "Nº SKUs Críticos"],
        horizontal=True
    )

    pivot_valor = df_critico.pivot_table(
        index="departamento",
        columns="filial_nome",
        values="valor_custo",
        aggfunc="sum",
        fill_value=0
    )

    pivot_pct = df.pivot_table(
        index="departamento",
        columns="filial_nome",
        values="critico",
        aggfunc=lambda x: (x.sum() / len(x) * 100) if len(x) > 0 else 0,
        fill_value=0
    )

    pivot_n = df_critico.pivot_table(
        index="departamento",
        columns="filial_nome",
        values="codigo_sku",
        aggfunc="nunique",
        fill_value=0
    )

    if opcao_heatmap == "Valor Parado (R$)":
        pivot = pivot_valor
        fmt   = ".0f"
        titulo_cb = "R$"
    elif opcao_heatmap == "% SKUs Críticos":
        pivot = pivot_pct
        fmt   = ".1f"
        titulo_cb = "%"
    else:
        pivot = pivot_n
        fmt   = ".0f"
        titulo_cb = "SKUs"

    fig_heat = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale="Reds",
        text=[[f"{v:{fmt}}" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont={"size": 11},
        hovertemplate="Depto: %{y}<br>Filial: %{x}<br>Valor: %{z}<extra></extra>",
        colorbar=dict(title=titulo_cb)
    ))
    fig_heat.update_layout(
        height=340,
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="white",
        xaxis=dict(tickangle=-35),
        title=f"Heatmap: {opcao_heatmap}"
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 4 — Detalhamento por departamento selecionado
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("🔍 Detalhamento por Departamento")

    deptos_lista = ["Selecione..."] + sorted(
        df["departamento"].dropna().unique().tolist()
    )
    depto_sel = st.selectbox("Escolha um departamento:", deptos_lista)

    if depto_sel != "Selecione...":
        df_dep = df[df["departamento"] == depto_sel]
        df_dep_crit = df_dep[df_dep["critico"] == True]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total SKUs",      formatar_int(df_dep["codigo_sku"].nunique()))
        m2.metric("SKUs Críticos",   formatar_int(df_dep_crit["codigo_sku"].nunique()))
        m3.metric("Valor Parado",    formatar_brl(df_dep_crit["valor_custo"].sum()))
        m4.metric("% Crítico",       formatar_pct(
            df_dep_crit["codigo_sku"].nunique() /
            max(df_dep["codigo_sku"].nunique(), 1) * 100
        ))

        # Top 10 SKUs críticos do departamento
        top_sku = (
            df_dep_crit
            .groupby(["codigo_sku", "descricao"])
            .agg(
                valor=("valor_custo", "sum"),
                dias=("dias_estoque", "max"),
                filiais=("filial_nome", "nunique")
            )
            .reset_index()
            .sort_values("valor", ascending=False)
            .head(10)
        )
        top_sku["Valor Parado"] = top_sku["valor"].apply(formatar_brl)
        top_sku["Dias"]         = top_sku["dias"].apply(lambda x: f"{x:.0f}d")
        top_sku["Filiais"]      = top_sku["filiais"].apply(formatar_int)

        st.markdown(f"**Top 10 SKUs Críticos — {depto_sel}**")
        st.dataframe(
            top_sku[[
                "codigo_sku", "descricao", "Dias",
                "Filiais", "Valor Parado"
            ]].rename(columns={
                "codigo_sku": "SKU",
                "descricao":  "Descrição"
            }),
            use_container_width=True,
            hide_index=True
        )
