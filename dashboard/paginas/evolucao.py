# dashboard/paginas/evolucao.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from componentes.kpis import formatar_brl, formatar_int, formatar_pct

# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE AGREGAÇÃO TEMPORAL
# ─────────────────────────────────────────────────────────────────────────────

def agregar_por_periodo(df, freq):
    """
    Agrega o DataFrame por frequência temporal.
    freq: 'D' (diário), 'W' (semanal), 'SM' (quinzenal), 'M' (mensal)
    """
    df = df.copy()
    df["periodo"] = df["data_arquivo"].dt.to_period(freq).dt.start_time

    agregado = df.groupby("periodo").agg(
        valor_parado   = ("valor_custo",  lambda x: x[df.loc[x.index, "critico"]].sum()),
        skus_criticos  = ("critico",      "sum"),
        total_skus     = ("codigo_sku",   "nunique"),
        valor_total    = ("valor_custo",  "sum"),
    ).reset_index()

    agregado["pct_critico"] = (
        agregado["skus_criticos"] / agregado["total_skus"] * 100
    ).fillna(0)

    return agregado

def agregar_por_periodo_depto(df, freq):
    """Agrega por período + departamento."""
    df = df.copy()
    df["periodo"] = df["data_arquivo"].dt.to_period(freq).dt.start_time

    return df[df["critico"] == True].groupby(
        ["periodo", "departamento"]
    ).agg(
        valor_parado  = ("valor_custo", "sum"),
        skus_criticos = ("codigo_sku",  "nunique"),
    ).reset_index()

def agregar_por_periodo_filial(df, freq):
    """Agrega por período + filial."""
    df = df.copy()
    df["periodo"] = df["data_arquivo"].dt.to_period(freq).dt.start_time

    return df[df["critico"] == True].groupby(
        ["periodo", "filial_nome", "uf"]
    ).agg(
        valor_parado  = ("valor_custo", "sum"),
        skus_criticos = ("codigo_sku",  "nunique"),
    ).reset_index()

# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def pagina_evolucao(df_total, filtros):
    """Aba 6 — Evolução temporal com múltiplas granularidades."""

    if df_total.empty:
        st.warning("Nenhum dado disponível.")
        return

    st.subheader("📈 Evolução Temporal do Estoque Crítico")

    # Aplicar filtros de filial/depto/estado ao histórico completo
    df = df_total.copy()
    if filtros.get("estado") and filtros["estado"] != "Todos":
        df = df[df["uf"] == filtros["estado"]]
    if filtros.get("departamento") and filtros["departamento"] != "Todos":
        df = df[df["departamento"] == filtros["departamento"]]
    if filtros.get("filial") and filtros["filial"] != "Todas":
        df = df[df["filial_nome"] == filtros["filial"]]

    if df["data_arquivo"].nunique() < 2:
        st.info(
            "📅 São necessários dados de **pelo menos 2 datas** para exibir a evolução. "
            "Continue subindo os CSVs diários!"
        )
        return

    # ── Seletor de granularidade ──────────────────────────────────────────────
    col_g1, col_g2 = st.columns([2, 4])

    with col_g1:
        granularidade = st.radio(
            "Granularidade:",
            ["Diário", "Semanal", "Quinzenal", "Mensal"],
            horizontal=True
        )

    freq_map = {
        "Diário":    "D",
        "Semanal":   "W",
        "Quinzenal": "SM",
        "Mensal":    "M"
    }
    freq = freq_map[granularidade]

    with col_g2:
        metrica = st.radio(
            "Métrica principal:",
            ["Valor Parado (R$)", "SKUs Críticos", "% Crítico"],
            horizontal=True
        )

    metrica_col = {
        "Valor Parado (R$)": "valor_parado",
        "SKUs Críticos":     "skus_criticos",
        "% Crítico":         "pct_critico"
    }[metrica]

    # ── Dados agregados ───────────────────────────────────────────────────────
    df_agg = agregar_por_periodo(df, freq)

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 1 — Gráfico principal de evolução
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader(f"📊 Evolução {granularidade} — {metrica}")

    fig_principal = go.Figure()

    # Linha principal
    fig_principal.add_trace(go.Scatter(
        x=df_agg["periodo"],
        y=df_agg[metrica_col],
        mode="lines+markers",
        name=metrica,
        line=dict(color="#e74c3c", width=3),
        marker=dict(size=8),
        fill="tozeroy",
        fillcolor="rgba(231,76,60,0.15)"
    ))

    # Anotação do último valor
    if not df_agg.empty:
        ultimo = df_agg.iloc[-1]
        fig_principal.add_annotation(
            x=ultimo["periodo"],
            y=ultimo[metrica_col],
            text=f"<b>{formatar_brl(ultimo[metrica_col]) if 'Valor' in metrica else f'{ultimo[metrica_col]:.1f}'}</b>",
            showarrow=True,
            arrowhead=2,
            bgcolor="#e74c3c",
            font=dict(color="white", size=12)
        )

    fig_principal.update_layout(
        height=420,
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="white",
        xaxis=dict(title="Período", gridcolor="#2a2f3e"),
        yaxis=dict(title=metrica, gridcolor="#2a2f3e"),
        hovermode="x unified"
    )
    st.plotly_chart(fig_principal, use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 2 — Comparativo D-1 / D-7 / D-15 / D-30 / YTD
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📅 Comparativos de Período")

    data_max   = df["data_arquivo"].max()
    valor_hoje = df_agg[df_agg["periodo"] == df_agg["periodo"].max()][metrica_col]
    valor_hoje = float(valor_hoje.values[0]) if not valor_hoje.empty else 0

    def valor_em(dias_atras):
        data_alvo = data_max - pd.Timedelta(days=dias_atras)
        # Pegar a data disponível mais próxima
        datas_disp = df["data_arquivo"].dt.normalize().unique()
        datas_disp = sorted(datas_disp)
        data_mais_prox = min(
            datas_disp,
            key=lambda d: abs((d - data_alvo).days),
            default=None
        )
        if data_mais_prox is None:
            return None
        df_ref = df[df["data_arquivo"].dt.normalize() == data_mais_prox]
        if df_ref.empty:
            return None
        if metrica_col == "valor_parado":
            return float(df_ref[df_ref["critico"] == True]["valor_custo"].sum())
        elif metrica_col == "skus_criticos":
            return float(df_ref["critico"].sum())
        elif metrica_col == "pct_critico":
            total = df_ref["codigo_sku"].nunique()
            crit  = df_ref["critico"].sum()
            return float(crit / total * 100) if total > 0 else 0
        return None

    def delta_fmt(v_atual, v_ant):
        if v_ant is None or v_ant == 0:
            return None, None
        delta = v_atual - v_ant
        pct   = delta / v_ant * 100
        return delta, pct

    periodos = {
        "D-1":  valor_em(1),
        "D-7":  valor_em(7),
        "D-15": valor_em(15),
        "D-30": valor_em(30),
    }

    # YTD: primeiro dia do ano
    primeiro_dia_ano = pd.Timestamp(data_max.year, 1, 1)
    df_ytd_start = df[df["data_arquivo"].dt.normalize() == primeiro_dia_ano]
    if not df_ytd_start.empty:
        if metrica_col == "valor_parado":
            periodos["YTD"] = float(
                df_ytd_start[df_ytd_start["critico"] == True]["valor_custo"].sum()
            )
        elif metrica_col == "skus_criticos":
            periodos["YTD"] = float(df_ytd_start["critico"].sum())
        else:
            total_ytd = df_ytd_start["codigo_sku"].nunique()
            crit_ytd  = df_ytd_start["critico"].sum()
            periodos["YTD"] = float(crit_ytd / total_ytd * 100) if total_ytd > 0 else 0
    else:
        periodos["YTD"] = None

    cols_comp = st.columns(len(periodos))
    for i, (label, v_ant) in enumerate(periodos.items()):
        delta_abs, delta_pct = delta_fmt(valor_hoje, v_ant)
        with cols_comp[i]:
            if "Valor" in metrica:
                val_fmt   = formatar_brl(valor_hoje)
                delta_str = (
                    f"{formatar_brl(delta_abs)} ({delta_pct:+.1f}%)"
                    if delta_abs is not None else None
                )
            else:
                val_fmt   = f"{valor_hoje:.1f}"
                delta_str = (
                    f"{delta_abs:+.1f} ({delta_pct:+.1f}%)"
                    if delta_abs is not None else None
                )
            st.metric(
                f"vs {label}",
                val_fmt,
                delta=delta_str,
                delta_color="inverse"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 3 — Evolução por Departamento
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader(f"📂 Evolução por Departamento — {granularidade}")

    df_agg_dep = agregar_por_periodo_depto(df, freq)

    if not df_agg_dep.empty:
        fig_dep = px.line(
            df_agg_dep,
            x="periodo", y="valor_parado",
            color="departamento",
            markers=True,
            labels={
                "periodo":       "Período",
                "valor_parado":  "Valor Parado (R$)",
                "departamento":  "Departamento"
            },
            title=f"Valor Parado Crítico por Departamento — {granularidade}"
        )
        fig_dep.update_layout(
            height=400,
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white",
            xaxis=dict(gridcolor="#2a2f3e"),
            yaxis=dict(gridcolor="#2a2f3e"),
            hovermode="x unified"
        )
        st.plotly_chart(fig_dep, use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 4 — Evolução por Filial (Top 5)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader(f"🏪 Evolução por Filial — Top 5 (Valor Parado)")

    df_agg_fil = agregar_por_periodo_filial(df, freq)

    if not df_agg_fil.empty:
        # Selecionar top 5 filiais por valor total
        top5_filiais = (
            df_agg_fil.groupby("filial_nome")["valor_parado"]
            .sum()
            .nlargest(5)
            .index.tolist()
        )

        col_top5, _ = st.columns([3, 1])
        with col_top5:
            filiais_opcoes = ["Top 5 automático"] + sorted(
                df_agg_fil["filial_nome"].unique().tolist()
            )
            sel_filiais = st.multiselect(
                "Selecionar filiais:",
                options=sorted(df_agg_fil["filial_nome"].unique().tolist()),
                default=top5_filiais,
                max_selections=8
            )

        filiais_filtro = sel_filiais if sel_filiais else top5_filiais
        df_fil_plot = df_agg_fil[df_agg_fil["filial_nome"].isin(filiais_filtro)]

        fig_fil = px.line(
            df_fil_plot,
            x="periodo", y="valor_parado",
            color="filial_nome",
            markers=True,
            labels={
                "periodo":      "Período",
                "valor_parado": "Valor Parado (R$)",
                "filial_nome":  "Filial"
            },
            title=f"Valor Parado Crítico por Filial — {granularidade}"
        )
        fig_fil.update_layout(
            height=420,
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white",
            xaxis=dict(gridcolor="#2a2f3e"),
            yaxis=dict(gridcolor="#2a2f3e"),
            hovermode="x unified"
        )
        st.plotly_chart(fig_fil, use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 5 — Tabela resumo histórico
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📋 Ver tabela resumo histórico completo"):
        df_resumo = df_agg.copy()
        df_resumo["periodo"]       = df_resumo["periodo"].dt.strftime("%d/%m/%Y")
        df_resumo["valor_parado"]  = df_resumo["valor_parado"].apply(formatar_brl)
        df_resumo["valor_total"]   = df_resumo["valor_total"].apply(formatar_brl)
        df_resumo["pct_critico"]   = df_resumo["pct_critico"].apply(formatar_pct)
        df_resumo["skus_criticos"] = df_resumo["skus_criticos"].apply(formatar_int)
        df_resumo["total_skus"]    = df_resumo["total_skus"].apply(formatar_int)

        st.dataframe(
            df_resumo.rename(columns={
                "periodo":       "Período",
                "valor_parado":  "Valor Parado",
                "skus_criticos": "SKUs Críticos",
                "total_skus":    "Total SKUs",
                "valor_total":   "Valor Total",
                "pct_critico":   "% Crítico"
            }),
            use_container_width=True,
            hide_index=True
        )
