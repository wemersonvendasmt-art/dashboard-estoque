# dashboard/paginas/produtos_criticos.py
import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from componentes.kpis import formatar_brl, formatar_int, formatar_pct

# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE SUGESTÃO ACIONÁVEL
# ─────────────────────────────────────────────────────────────────────────────

def gerar_sugestao(row):
    dias   = float(row.get("dias_estoque") or 0)
    giro   = float(row.get("giro")         or 0)
    mkp    = float(row.get("mkp_pct")      or 0)
    saldo  = float(row.get("saldo")        or 0)
    valor  = float(row.get("valor_custo")  or 0)

    if dias >= 365:
        return "🔴 LIQUIDAR — Parado há mais de 1 ano"
    if dias >= 90 and giro == 0 and mkp >= 20:
        return "🟠 PROMOÇÃO/MARKDOWN — Alto valor, margem suficiente"
    if dias >= 90 and giro == 0 and mkp < 20:
        return "🔴 CONGELAR COMPRA — Sem giro e margem baixa"
    if dias >= 90 and giro > 0 and saldo > 0:
        return "🟡 MONITORAR — Tem giro mas estoque alto"
    if dias >= 90 and valor >= 1000:
        return "🟠 TRANSFERÊNCIA — Verificar demanda em outras filiais"
    if dias >= 90:
        return "🟡 REVISAR — Crítico sem ação clara definida"
    return "✅ Normal"

def gerar_lista_transferencias(df):
    if "data_arquivo" not in df.columns or df["data_arquivo"].isna().all():
        return pd.DataFrame()

    data_ref = pd.to_datetime(df["data_arquivo"]).max()
    limite_venda_recente = data_ref - pd.Timedelta(days=30)

    criticos = df[
        (df["critico"] == True) &
        (df["giro"].fillna(0) == 0)
    ][["codigo_sku", "descricao", "filial_nome", "saldo",
       "valor_custo", "dias_estoque"]].copy()

    criticos = criticos.rename(columns={
        "filial_nome":  "filial_origem",
        "saldo":        "saldo_origem",
        "valor_custo":  "valor_origem",
        "dias_estoque": "dias_origem"
    })

    if "ultima_venda" not in df.columns:
        return pd.DataFrame()

    df_uv = df.copy()
    df_uv["ultima_venda"] = pd.to_datetime(df_uv["ultima_venda"], errors="coerce")

    com_venda = df_uv[
        df_uv["ultima_venda"].notna() &
        (df_uv["ultima_venda"] >= limite_venda_recente) &
        (df_uv["giro"].fillna(0) > 0)
    ][["codigo_sku", "filial_nome", "ultima_venda", "giro"]].copy()

    com_venda = com_venda.rename(columns={
        "filial_nome": "filial_destino",
        "giro":        "giro_destino"
    })

    sugestoes = criticos.merge(com_venda, on="codigo_sku", how="inner")
    sugestoes = sugestoes[
        sugestoes["filial_origem"] != sugestoes["filial_destino"]
    ]

    if sugestoes.empty:
        return pd.DataFrame()

    sugestoes["qty_sugerida"] = (sugestoes["saldo_origem"] * 0.5).apply(
        lambda x: max(1, round(float(x))) if pd.notna(x) else 1
    )
    sugestoes["impacto_estimado"] = (
        sugestoes["qty_sugerida"] /
        sugestoes["saldo_origem"].replace(0, 1) *
        sugestoes["valor_origem"]
    )

    return sugestoes[[
        "codigo_sku", "descricao",
        "filial_origem", "saldo_origem", "dias_origem",
        "filial_destino", "giro_destino", "ultima_venda",
        "qty_sugerida", "impacto_estimado"
    ]].sort_values("impacto_estimado", ascending=False)

def exportar_excel(df_export):
    """Gera arquivo Excel em memória para download."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Dados")
    return output.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def pagina_produtos_criticos(df):
    if df.empty:
        st.warning("Nenhum dado para os filtros selecionados.")
        return

    st.subheader("🚨 Produtos Críticos — Lista Acionável")

    df_critico = df[df["critico"] == True].copy()

    # Garantir codigo_sku como string
    if "codigo_sku" in df_critico.columns:
        df_critico["codigo_sku"] = df_critico["codigo_sku"].astype(str)

    if df_critico.empty:
        st.success("✅ Nenhum item crítico encontrado para os filtros selecionados!")
        return

    # ── KPIs rápidos ──────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("SKUs Críticos",    formatar_int(df_critico["codigo_sku"].nunique()))
    k2.metric("Valor Parado",     formatar_brl(df_critico["valor_custo"].sum()))
    k3.metric("Dias Médio",       f"{df_critico['dias_estoque'].mean():.0f}d")
    k4.metric("Filiais Afetadas", formatar_int(df_critico["filial_nome"].nunique()))

    st.markdown("---")

    sub1, sub2, sub3 = st.tabs([
        "📋 Tabela Completa",
        "🔄 Transferências Sugeridas",
        "📌 Por Ação Recomendada"
    ])

    # ═══════════════════════════════════════════════════════════════════════
    # SUB-ABA 1 — Tabela completa
    # ═══════════════════════════════════════════════════════════════════════
    with sub1:
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)

        with col_f1:
            busca = st.text_input(
                "🔍 Buscar SKU ou descrição",
                placeholder="Ex: ração, 0017687..."
            )
        with col_f2:
            filiais_lista = ["Todas"] + sorted(
                df_critico["filial_nome"].dropna().unique().tolist()
            )
            filial_sel = st.selectbox("Filial", filiais_lista, key="pc_filial")

        with col_f3:
            deptos_lista = ["Todos"] + sorted(
                df_critico["departamento"].dropna().unique().tolist()
            )
            depto_sel = st.selectbox("Departamento", deptos_lista, key="pc_depto")

        with col_f4:
            ordenar_por = st.selectbox(
                "Ordenar por",
                ["Valor Parado ↓", "Dias Parado ↓", "Saldo ↓", "Giro ↑"]
            )

        df_view = df_critico.copy()

        if busca:
            mask = (
                df_view["codigo_sku"].str.contains(busca, case=False, na=False) |
                df_view["descricao"].astype(str).str.contains(busca, case=False, na=False)
            )
            df_view = df_view[mask]

        if filial_sel != "Todas":
            df_view = df_view[df_view["filial_nome"] == filial_sel]

        if depto_sel != "Todos":
            df_view = df_view[df_view["departamento"] == depto_sel]

        ordem_map = {
            "Valor Parado ↓": ("valor_custo",  False),
            "Dias Parado ↓":  ("dias_estoque", False),
            "Saldo ↓":        ("saldo",        False),
            "Giro ↑":         ("giro",         True),
        }
        col_ord, asc_ord = ordem_map[ordenar_por]
        if col_ord in df_view.columns:
            df_view = df_view.sort_values(col_ord, ascending=asc_ord)

        df_view["sugestao"] = df_view.apply(gerar_sugestao, axis=1)

        colunas_exibir = [
            c for c in [
                "filial_nome", "departamento", "codigo_sku", "descricao",
                "saldo", "dias_estoque", "ultima_venda", "ultima_entrada",
                "giro", "valor_custo", "valor_venda", "mkp_pct",
                "venda_m0", "venda_m1", "venda_m2",
                "fornecedor", "sugestao"
            ] if c in df_view.columns
        ]

        # Guardar cópia numérica para exportação ANTES de formatar
        df_export_raw = df_view[colunas_exibir].copy()

        df_exibir = df_view[colunas_exibir].copy()

        for col_moeda in ["valor_custo", "valor_venda", "venda_m0", "venda_m1", "venda_m2"]:
            if col_moeda in df_exibir.columns:
                df_exibir[col_moeda] = df_exibir[col_moeda].apply(
                    lambda x: formatar_brl(x) if pd.notna(x) else "-"
                )

        if "mkp_pct" in df_exibir.columns:
            df_exibir["mkp_pct"] = df_exibir["mkp_pct"].apply(
                lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
            )

        if "dias_estoque" in df_exibir.columns:
            df_exibir["dias_estoque"] = df_exibir["dias_estoque"].apply(
                lambda x: f"{x:.0f}d" if pd.notna(x) else "-"
            )

        rename_map = {
            "filial_nome":    "Filial",
            "departamento":   "Depto",
            "codigo_sku":     "SKU",
            "descricao":      "Descrição",
            "saldo":          "Saldo",
            "dias_estoque":   "Dias",
            "ultima_venda":   "Últ. Venda",
            "ultima_entrada": "Últ. Entrada",
            "giro":           "Giro",
            "valor_custo":    "Custo (R$)",
            "valor_venda":    "Venda (R$)",
            "mkp_pct":        "%MKP",
            "venda_m0":       "Venda M0",
            "venda_m1":       "Venda M1",
            "venda_m2":       "Venda M2",
            "fornecedor":     "Fornecedor",
            "sugestao":       "⚡ Ação"
        }
        df_exibir = df_exibir.rename(columns=rename_map)

        st.markdown(
            f"**{formatar_int(len(df_view))} itens críticos encontrados** "
            f"| Valor total: **{formatar_brl(df_view['valor_custo'].sum())}**"
        )

        st.dataframe(
            df_exibir,
            use_container_width=True,
            hide_index=True,
            height=500
        )

        col_exp1, col_exp2, _ = st.columns([1, 1, 3])

        with col_exp1:
            csv_bytes = df_export_raw.to_csv(
                index=False, sep=";", encoding="utf-8-sig"
            ).encode("utf-8-sig")
            st.download_button(
                label="⬇️ Exportar CSV",
                data=csv_bytes,
                file_name="produtos_criticos.csv",
                mime="text/csv"
            )

        with col_exp2:
            excel_bytes = exportar_excel(df_export_raw)
            st.download_button(
                label="⬇️ Exportar Excel",
                data=excel_bytes,
                file_name="produtos_criticos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # ═══════════════════════════════════════════════════════════════════════
    # SUB-ABA 2 — Transferências sugeridas
    # ═══════════════════════════════════════════════════════════════════════
    with sub2:
        st.markdown("""
        ### 🔄 Sugestões de Transferência entre Filiais

        **Lógica:** SKU crítico (≥90d, giro=0) na **Filial Origem** com venda
        nos últimos 30 dias na **Filial Destino**. Quantidade sugerida = 50% do saldo parado.
        """)

        with st.spinner("Calculando sugestões de transferência..."):
            df_transf = gerar_lista_transferencias(df)

        if df_transf.empty:
            st.info(
                "ℹ️ Nenhuma sugestão de transferência encontrada. "
                "Isso pode indicar que os itens críticos não têm demanda "
                "em nenhuma outra filial no período recente."
            )
        else:
            t1, t2, t3 = st.columns(3)
            t1.metric("SKUs com sugestão",  formatar_int(df_transf["codigo_sku"].nunique()))
            t2.metric("Impacto estimado",   formatar_brl(df_transf["impacto_estimado"].sum()))
            t3.metric("Pares Origem→Destino", formatar_int(len(df_transf)))

            impacto_destino = (
                df_transf.groupby("filial_destino")["impacto_estimado"]
                .sum().reset_index()
                .sort_values("impacto_estimado", ascending=False)
            )
            fig_transf = px.bar(
                impacto_destino,
                x="filial_destino", y="impacto_estimado",
                color="impacto_estimado",
                color_continuous_scale="Greens",
                labels={"filial_destino": "Filial Destino", "impacto_estimado": "Impacto (R$)"},
                text=impacto_destino["impac
