# etl/config.py
# Configurações centrais do ETL

# ── Separador do CSV exportado pelo QlikView ──────────────────────────────────
CSV_SEPARADOR = ";"

# ── Encoding dos arquivos CSV ─────────────────────────────────────────────────
CSV_ENCODING = "utf-8-sig"   # utf-8-sig lida com BOM (ï»¿) do QlikView

# ── Linha de totais (segunda linha do CSV — ignorar no ETL) ───────────────────
PULAR_LINHA_TOTAIS = True    # linha 2 do CSV é totais gerais, não produto

# ── Critério de item CRÍTICO ──────────────────────────────────────────────────
DIAS_CRITICO = 90

# ── Mapeamento de colunas do CSV para nomes internos ─────────────────────────
MAPA_COLUNAS = {
    "Produto"          : "sku_raw",
    "Última Venda"     : "ultima_venda",
    "Última Entrada"   : "ultima_entrada",
    "Saldo"            : "saldo",
    "Giro"             : "giro",
    "Dias Est"         : "dias_estoque",
    "Saldo Compra R$"  : "valor_custo",
    "UN Compra R$"     : "custo_unitario",
    "Saldo Venda R$"   : "valor_venda",
    "%MKP"             : "mkp_pct",
    "UN Venda R$"      : "preco_venda",
}

# ── Colunas de vendas mensais (detectadas automaticamente pelo ETL) ───────────
# Qualquer coluna que não esteja no MAPA_COLUNAS e contenha mês/ano
# será capturada como venda_m0, venda_m1, venda_m2 (ordem = mais recente primeiro)

# ── Caminhos de pastas ────────────────────────────────────────────────────────
import os

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_UPLOADS   = os.path.join(BASE_DIR, "dados", "uploads")
DIR_HISTORICO = os.path.join(BASE_DIR, "dados", "historico")
DIR_DIMENSOES = os.path.join(BASE_DIR, "dados", "dimensoes")

ARQUIVO_HISTORICO  = os.path.join(DIR_HISTORICO, "historico_consolidado.parquet")
ARQUIVO_FILIAIS    = os.path.join(DIR_DIMENSOES, "dim_filiais.csv")
ARQUIVO_DEPTOS     = os.path.join(DIR_DIMENSOES, "dim_deptos.csv")
ARQUIVO_PRODUTOS   = os.path.join(DIR_DIMENSOES, "dim_produtos.csv")
ARQUIVO_PROCESSADOS = os.path.join(DIR_HISTORICO, "arquivos_processados.txt")
