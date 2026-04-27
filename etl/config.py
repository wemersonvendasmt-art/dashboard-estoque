# etl/config.py
import os

# ── Diretórios base ───────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_DADOS       = os.path.join(BASE_DIR, "dados")
DIR_UPLOADS     = os.path.join(DIR_DADOS, "uploads")
DIR_HISTORICO   = os.path.join(DIR_DADOS, "historico")
DIR_DIMENSOES   = os.path.join(DIR_DADOS, "dimensoes")

# Criar diretórios se não existirem
for _d in [DIR_UPLOADS, DIR_HISTORICO, DIR_DIMENSOES]:
    os.makedirs(_d, exist_ok=True)

# ── Arquivo de histórico (Parquet local) ──────────────────────────────────────
ARQUIVO_HISTORICO   = os.path.join(DIR_HISTORICO, "historico.parquet")
ARQUIVO_PROCESSADOS = os.path.join(DIR_HISTORICO, "arquivos_processados.txt")

# ── Dimensões ─────────────────────────────────────────────────────────────────
ARQUIVO_FILIAIS  = os.path.join(DIR_DIMENSOES, "dim_filiais.csv")
ARQUIVO_DEPTOS   = os.path.join(DIR_DIMENSOES, "dim_deptos.csv")
ARQUIVO_PRODUTOS = os.path.join(DIR_DIMENSOES, "dim_produtos.csv")

# ── Configurações do CSV (QlikView) ───────────────────────────────────────────
CSV_SEPARADOR = ";"
CSV_ENCODING  = "utf-8-sig"   # lida com BOM (ï»¿)

# ── Critério de item CRÍTICO ──────────────────────────────────────────────────
DIAS_CRITICO = 90

# ── Mapeamento de colunas CSV → nomes internos ────────────────────────────────
MAPA_COLUNAS = {
    "Produto"         : "sku_raw",
    "Última Venda"    : "ultima_venda",
    "Última Entrada"  : "ultima_entrada",
    "Saldo"           : "saldo",
    "Giro"            : "giro",
    "Dias Est"        : "dias_estoque",
    "Saldo Compra R$" : "valor_custo",
    "UN Compra R$"    : "custo_unitario",
    "Saldo Venda R$"  : "valor_venda",
    "%MKP"            : "mkp_pct",
    "UN Venda R$"     : "preco_venda",
}
