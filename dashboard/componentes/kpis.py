# dashboard/componentes/kpis.py
import streamlit as st
import pandas as pd

def card_kpi(titulo, valor, delta=None, delta_label="vs D-1", cor_delta_positivo="inverse"):
    """
    Renderiza um card KPI com delta opcional.
    cor_delta_positivo: 'normal' (verde=sobe) ou 'inverse' (verde=cai — para valor parado)
    """
    st.metric(
        label=titulo,
        value=valor,
        delta=delta,
        delta_color=cor_delta_positivo
    )

def formatar_brl(valor):
    if valor is None or pd.isna(valor):
        return "R$‌ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_pct(valor):
    if valor is None or pd.isna(valor):
        return "0,0%"
    return f"{valor:.1f}%"

def formatar_int(valor):
    if valor is None or pd.isna(valor):
        return "0"
    return f"{int(valor):,}".replace(",", ".")

def calcular_kpis(df):
    """
    Recebe DataFrame já filtrado e retorna dict com KPIs calculados.
    """
    kpis = {}

    kpis["total_skus"]       = df["codigo_sku"].nunique()
    kpis["total_registros"]  = len(df)

    # SKUs sem giro (giro == 0 ou None)
    sem_giro = df[df["giro"].fillna(0) == 0]
    kpis["skus_sem_giro"]    = sem_giro["codigo_sku"].nunique()

    # SKUs críticos (>= 90 dias)
    criticos = df[df["critico"] == True]
    kpis["skus_criticos"]    = criticos["codigo_sku"].nunique()
    kpis["pct_critico"]      = (
        kpis["skus_criticos"] / kpis["total_skus"] * 100
        if kpis["total_skus"] > 0 else 0
    )

    # Valores financeiros
    kpis["valor_total"]      = df["valor_custo"].sum()
    kpis["valor_parado"]     = criticos["valor_custo"].sum()
    kpis["pct_valor_parado"] = (
        kpis["valor_parado"] / kpis["valor_total"] * 100
        if kpis["valor_total"] > 0 else 0
    )

    # Potencial de margem (valor_venda - valor_custo dos críticos)
    if "valor_venda" in criticos.columns:
        kpis["potencial_margem"] = (
            criticos["valor_venda"].sum() - criticos["valor_custo"].sum()
        )
    else:
        kpis["potencial_margem"] = 0

    return kpis

def calcular_delta(kpis_atual, kpis_anterior, campo):
    """Calcula variação absoluta e percentual entre dois períodos."""
    if kpis_anterior is None:
        return None, None
    v_atual = kpis_atual.get(campo, 0) or 0
    v_ant   = kpis_anterior.get(campo, 0) or 0
    delta_abs = v_atual - v_ant
    delta_pct = (delta_abs / v_ant * 100) if v_ant != 0 else 0
    return delta_abs, delta_pct
