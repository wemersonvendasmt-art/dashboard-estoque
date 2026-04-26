# dashboard/paginas/visao_geral.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from componentes.kpis import (
    calcular_kpis, formatar_brl, formatar_pct,
    formatar_int, calcular_delta
)

def pagina_visao_geral(df, df_total, filtros):
    """Aba 1 — Visão Geral com KPIs, alertas e gráficos."""

    if df.empty:
        st.warning("Nenhum dado para os filtros selecionados.")
        return

    # ── KPIs do período atual ─────────────────────────────────────────────────
    kpis = calcular_kpis(df)

    # ── KPIs de períodos anteriores para delta ────────────────────────────────
    data_ref = filtros.get("data_fim") or df["data_arquivo"].dt.date.max()

    def kpis_periodo_anterior(dias_atras):
        data_ant = pd.Timestamp(data_ref) - pd.Timedelta(days=dias_atras)
        df_ant = df_total[df_total["data_arquivo"].dt.date == data_ant.date()]
        # Aplicar mesmos filtros de filial/depto/estado
        if filtros.get("estado") and filtros["estado"] != "Todos":
            df_ant = df_ant[df_ant["uf"] == filtros["estado"]]
        if filtros.get("departamento") and filtros["departamento"] != "Todos":
            df_ant = df_ant[df_ant["departamento"] == filtros["departamento"]]
        if filtros.get("filial") and filtros["filial"] != "Todas":
            df_ant = df_ant[df_ant["filial_nome"] == filtros["filial"]]
        return calcular_kpis(df_ant) if not df_ant.empty else None

    kpis_d1  = kpis_periodo_anterior(1)
    kpis_d7  = kpis_periodo_anterior(7)
    kpis_d30 = kpis_periodo_anterior(30)

    # ── Linha 1: KPIs principais ──────────────────────────────────────────────
    st.subheader("📊 KPIs Principais")
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        delta_abs, _ = calcular_delta(kpis, kpis_d1, "total_skus")
        st.metric(
            "Total de SKUs",
            formatar_int(kpis["total_skus"]),
            delta=f"{delta_abs:+.0f} vs D-1" if delta_abs is not None else None,
            delta_color="off"
        )

    with c2:
        delta_abs, _ = calcular_delta(kpis, kpis_d1, "skus_criticos")
        st.metric(
            "SKUs Críticos (+90d)",
            formatar_int(kpis["skus_criticos"]),
            delta=f"{delta_abs:+.0f} vs D-1" if delta_abs is not None else None,
            delta_color="inverse"
        )

    with c3:
        delta_abs, _ = calcular_delta(kpis, kpis_d1, "skus_sem_giro")
        st.metric(
            "SKUs sem Giro",
            formatar_int(kpis["skus_sem_giro"]),
            delta=f"{delta_abs:+.0f} vs D-1" if delta_abs is not None else None,
            delta_color="inverse"
        )

    with c4:
        delta_abs, _ = calcular_delta(kpis, kpis_d1, "valor_parado")
        delta_fmt = formatar_brl(delta_abs) if delta_abs else None
        st.metric(
            "Valor Parado (R$)",
            formatar_brl(kpis["valor_parado"]),
            delta=f"{delta_fmt} vs D-1" if delta_fmt else None,
            delta_color="inverse"
        )

    with c5:
        st.metric(
            "% Valor Parado",
            formatar_pct(kpis["pct_valor_parado"]),
            delta=None
        )

    # ── Linha 2: KPIs secundários ─────────────────────────────────────────────
    st.markdown("---")
    c6, c7, c8, c9 = st.columns(4)

    with c6:
        st.metric("Valor Total Estoque", formatar_brl(kpis["valor_total"]))

    with c7:
        st.metric("Potencial de Margem", formatar_brl(kpis["potencial_margem"]))

    with c8:
        delta_abs7, delta_pct7 = calcular_delta(kpis, kpis_d7, "valor_parado")
        st.metric(
            "Valor Parado vs D-7",
            formatar_brl(kpis["valor_parado"]),
            delta=f"{formatar_brl(delta_abs7)} ({delta_pct7:+.1f}%)" if delta_abs7 else None,
            delta_color="inverse"
        )

    with c9:
        delta_abs30, delta_pct30 = calcular_delta(kpis, kpis_d30, "valor_parado")
        st.metric(
            "Valor Parado vs D-30",
            formatar_brl(kpis["valor_parado"]),
            delta=f"{formatar_brl(delta_abs30)} ({delta_pct30:+.1f}%)" if delta_abs30 else None,
            delta_color="inverse"
        )

    # ── Gráfico: Distribuição por bucket de dias ──────────────────────────────
    st.markdown("---")
    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        st.subheader("📊 SKUs por Faixa de Dias Parado")

        bins   = [0, 30, 60, 90, 180, 365, 99999]
        labels = ["0–30d", "31–60d", "61–90d", "91–180d", "181–365d", "365+d"]
        df_bucket = df.copy()
        df_bucket["faixa"] = pd.cut(
            df_bucket["dias_estoque"].fillna(0),
            bins=bins, labels=labels, right=True
        )
        contagem = df_bucket.groupby("faixa", observed=True).agg(
            qtd_skus=("codigo_sku", "nunique"),
            valor=("valor_custo", "sum")
        ).reset_index()

        fig1 = px.bar(
            contagem, x="faixa", y="qtd_skus",
            color="faixa",
            color_discrete_sequence=px.colors.sequential.Reds,
            labels={"faixa": "Faixa", "qtd_skus": "Qtd SKUs"},
            text="qtd_skus"
        )
        fig1.update_traces(textposition="outside")
        fig1.update_layout(
            showlegend=False, height=350,
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white"
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col_graf2:
        st.subheader("💰 Valor Parado por Faixa (R$)")
        fig2 = px.pie(
            contagem, names="faixa", values="valor",
            color_discrete_sequence=px.colors.sequential.RdBu,
            hole=0.4
        )
        fig2.update_layout(
            height=350,
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white"
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── ALERTAS ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🚨 Alertas")
    al1, al2, al3 = st.columns(3)

    # Top 10 itens críticos por valor
    with al1:
        st.markdown("**🔴 Top 10 Itens Críticos (R$)**")
        top_itens = (
            df[df["critico"] == True]
            .groupby(["codigo_sku", "descricao", "filial_nome"])
            .agg(valor=("valor_custo", "sum"), dias=("dias_estoque", "max"))
            .reset_index()
            .sort_values("valor", ascending=False)
            .head(10)
        )
        top_itens["valor_fmt"] = top_itens["valor"].apply(formatar_brl)
        st.dataframe(
            top_itens[["descricao", "filial_nome", "dias", "valor_fmt"]].rename(columns={
                "descricao": "Produto",
                "filial_nome": "Filial",
                "dias": "Dias",
                "valor_fmt": "Valor Parado"
            }),
            use_container_width=True,
            hide_index=True
        )

    # Top filiais com maior valor parado
    with al2:
        st.markdown("**🏪 Top Filiais — Valor Parado**")
        top_filiais = (
            df[df["critico"] == True]
            .groupby("filial_nome")
            .agg(valor=("valor_custo", "sum"), skus=("codigo_sku", "nunique"))
            .reset_index()
            .sort_values("valor", ascending=False)
        )
        fig_fil = px.bar(
            top_filiais, x="valor", y="filial_nome",
            orientation="h",
            color="valor",
            color_continuous_scale="Reds",
            labels={"valor": "R$", "filial_nome": "Filial"},
            text=top_filiais["valor"].apply(lambda x: formatar_brl(x))
        )
        fig_fil.update_traces(textposition="outside")
        fig_fil.update_layout(
            showlegend=False, height=350,
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white", coloraxis_showscale=False
        )
        st.plotly_chart(fig_fil, use_container_width=True)

    # Top departamentos com maior % crítico
    with al3:
        st.markdown("**📂 Top Departamentos — % Crítico**")
        df_depto = df.groupby("departamento").agg(
            total=("codigo_sku", "nunique"),
            criticos=("critico", "sum")
        ).reset_index()
        df_depto["pct"] = df_depto["criticos"] / df_depto["total"] * 100

        fig_dep = px.bar(
            df_depto.sort_values("pct", ascending=False),
            x="departamento", y="pct",
            color="pct",
            color_continuous_scale="Oranges",
            labels={"departamento": "Depto", "pct": "% Crítico"},
            text=df_depto.sort_values("pct", ascending=False)["pct"].apply(
                lambda x: f"{x:.1f}%"
            )
        )
        fig_dep.update_traces(textposition="outside")
        fig_dep.update_layout(
            showlegend=False, height=350,
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white", coloraxis_showscale=False
        )
        st.plotly_chart(fig_dep, use_container_width=True)
