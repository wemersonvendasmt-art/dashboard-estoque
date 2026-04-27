# dashboard/app.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "etl"))

import streamlit as st
import pandas as pd

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Estoque | Compras",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Imports internos ──────────────────────────────────────────────────────────
from config import ARQUIVO_HISTORICO, DIR_UPLOADS, DIR_HISTORICO
import processar

# ── CSS customizado ───────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stMetric { background: #1a1f2e; border-radius: 10px; padding: 12px; }
    .stMetric label { font-size: 13px !important; color: #aaa !important; }
    .stMetric [data-testid="stMetricValue"] { font-size: 22px !important; font-weight: 700; }
    .block-container { padding-top: 1rem; }
    h1 { color: #1f77b4; }
    .stTabs [data-baseweb="tab"] { font-size: 15px; font-weight: 600; }
    .upload-box { border: 2px dashed #1f77b4; border-radius: 10px; padding: 20px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# ── Carregar dados ────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def carregar_dados():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "etl"))
    import storage
    df = storage.carregar_historico()
    if df.empty:
        return df
    df["data_arquivo"] = pd.to_datetime(df["data_arquivo"], errors="coerce")
    return df
    
# ── Sidebar: Upload + Filtros ─────────────────────────────────────────────────
def sidebar_upload_e_filtros(df):
    st.sidebar.image(
        "https://img.icons8.com/fluency/96/box.png", width=60
    )
    st.sidebar.title("📦 Dashboard Estoque")
    st.sidebar.markdown("---")

    # ── Upload de CSVs ────────────────────────────────────────────────────────
    st.sidebar.subheader("📤 Subir CSVs do dia")
    arquivos_upload = st.sidebar.file_uploader(
        "Arraste os CSVs aqui (até 55 arquivos)",
        type=["csv"],
        accept_multiple_files=True,
        key="uploader"
    )

    if arquivos_upload:
        os.makedirs(DIR_UPLOADS, exist_ok=True)
        salvos = 0
        for arq in arquivos_upload:
            destino = os.path.join(DIR_UPLOADS, arq.name)
            with open(destino, "wb") as f:
                f.write(arq.read())
            salvos += 1
        st.sidebar.success(f"✅ {salvos} arquivo(s) salvo(s)!")

        if st.sidebar.button("▶️ Processar agora", type="primary"):
    with st.spinner("Processando CSVs..."):
    st.cache_data.clear()
    st.rerun()

    st.sidebar.markdown("---")

    # ── Filtros ───────────────────────────────────────────────────────────────
    filtros = {}

    if df.empty:
        st.sidebar.warning("Nenhum dado carregado ainda.")
        return filtros

    st.sidebar.subheader("🔍 Filtros")
    datas_disponiveis = sorted(df["data_arquivo"].dropna().dt.date.unique())

    if len(datas_disponiveis) >= 2:
        filtros["data_inicio"], filtros["data_fim"] = st.sidebar.date_input(
            "Período",
            value=(datas_disponiveis[-1], datas_disponiveis[-1]),
            min_value=datas_disponiveis[0],
            max_value=datas_disponiveis[-1]
        )
    else:
        filtros["data_inicio"] = datas_disponiveis[-1] if datas_disponiveis else None
        filtros["data_fim"] = filtros["data_inicio"]
        st.sidebar.info(f"Data: {filtros['data_inicio']}")

    estados = ["Todos"] + sorted(df["uf"].dropna().unique().tolist())
    filtros["estado"] = st.sidebar.selectbox("Estado (UF)", estados)

    deptos = ["Todos"] + sorted(df["departamento"].dropna().unique().tolist())
    filtros["departamento"] = st.sidebar.selectbox("Departamento", deptos)

    filiais = ["Todas"] + sorted(df["filial_nome"].dropna().unique().tolist())
    filtros["filial"] = st.sidebar.selectbox("Filial", filiais)

    filtros["somente_criticos"] = st.sidebar.checkbox(
        "⚠️ Somente críticos (+90 dias)", value=False
    )

    opcoes_bucket = [
        "Todos", "0–30 dias", "31–60 dias", "61–90 dias",
        "91–180 dias", "181–365 dias", "365+ dias"
    ]
    filtros["bucket"] = st.sidebar.selectbox("Faixa de dias", opcoes_bucket)

    filtros["giro_zero"] = st.sidebar.checkbox("Apenas giro = 0", value=False)

    val_max = float(df["valor_custo"].max() or 100000)
    filtros["valor_min"], filtros["valor_max"] = st.sidebar.slider(
        "Faixa de valor parado (R$)",
        min_value=0.0,
        max_value=val_max,
        value=(0.0, val_max),
        step=100.0,
        format="R$ %.0f"
    )

    return filtros
    
# ── Aplicar filtros ao DataFrame ──────────────────────────────────────────────
def aplicar_filtros(df, filtros):
    if df.empty or not filtros:
        return df

    # Filtro de data
    if filtros.get("data_inicio") and filtros.get("data_fim"):
        df = df[
            (df["data_arquivo"].dt.date >= filtros["data_inicio"]) &
            (df["data_arquivo"].dt.date <= filtros["data_fim"])
        ]

    # Estado
    if filtros.get("estado") and filtros["estado"] != "Todos":
        df = df[df["uf"] == filtros["estado"]]

    # Departamento
    if filtros.get("departamento") and filtros["departamento"] != "Todos":
        df = df[df["departamento"] == filtros["departamento"]]

    # Filial
    if filtros.get("filial") and filtros["filial"] != "Todas":
        df = df[df["filial_nome"] == filtros["filial"]]

    # Somente críticos
    if filtros.get("somente_criticos"):
        df = df[df["critico"] == True]

    # Bucket de dias
    bucket = filtros.get("bucket", "Todos")
    bucket_map = {
        "0–30 dias":    (0, 30),
        "31–60 dias":   (31, 60),
        "61–90 dias":   (61, 90),
        "91–180 dias":  (91, 180),
        "181–365 dias": (181, 365),
        "365+ dias":    (366, 99999),
    }
    if bucket in bucket_map:
        lo, hi = bucket_map[bucket]
        df = df[
            (df["dias_estoque"].fillna(0) >= lo) &
            (df["dias_estoque"].fillna(0) <= hi)
        ]

    # Giro zero
    if filtros.get("giro_zero"):
        df = df[df["giro"].fillna(0) == 0]

    # Faixa de valor
    if "valor_min" in filtros and "valor_max" in filtros:
        df = df[
            (df["valor_custo"].fillna(0) >= filtros["valor_min"]) &
            (df["valor_custo"].fillna(0) <= filtros["valor_max"])
        ]

    return df

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    df_total = carregar_dados()
    filtros  = sidebar_upload_e_filtros(df_total)
    df       = aplicar_filtros(df_total, filtros)

    st.title("📦 Dashboard de Estoque — Compras")

    if df_total.empty:
        st.info(
            "👈 Nenhum dado encontrado. Use o painel lateral para subir os CSVs do dia e clique em **Processar agora**."
        )
        return

    # ── Abas principais ───────────────────────────────────────────────────────
    aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
        "📊 Visão Geral",
        "🏪 Filiais",
        "🏭 Fornecedores",
        "📂 Departamentos",
        "🚨 Produtos Críticos",
        "📈 Evolução"
    ])

    with aba1:
        from paginas.visao_geral import pagina_visao_geral
        pagina_visao_geral(df, df_total, filtros)

    with aba2:
        from paginas.filiais import pagina_filiais
        pagina_filiais(df)

    with aba3:
        from paginas.fornecedores import pagina_fornecedores
        pagina_fornecedores(df)

    with aba4:
        from paginas.departamentos import pagina_departamentos
        pagina_departamentos(df)

    with aba5:
        from paginas.produtos_criticos import pagina_produtos_criticos
        pagina_produtos_criticos(df)

    with aba6:
        from paginas.evolucao import pagina_evolucao
        pagina_evolucao(df_total, filtros)

if __name__ == "__main__":
    main()
