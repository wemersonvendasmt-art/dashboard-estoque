COLUNAS_MINIMAS = {"codigo_sku", "descricao", "dias_estoque", "critico",
                   "filial_key", "departamento", "data_arquivo"}

def carregar_historico() -> pd.DataFrame:
    os.makedirs(DIR_HISTORICO, exist_ok=True)
    if not os.path.exists(ARQUIVO_HISTORICO):
        return pd.DataFrame()
    try:
        df = pd.read_parquet(ARQUIVO_HISTORICO)
        # Validar se tem colunas mínimas — se não, descarta
        if not COLUNAS_MINIMAS.issubset(set(df.columns)):
            print("[storage] ⚠️  Histórico incompatível, descartando.")
            return pd.DataFrame()
        return df
    except Exception as e:
        print(f"[storage] ⚠️  Erro ao carregar histórico: {e}")
        return pd.DataFrame()

# etl/storage.py — armazenamento local (sem Supabase, sem Google Drive)
import os
import pandas as pd
from config import ARQUIVO_HISTORICO, DIR_HISTORICO

def carregar_historico() -> pd.DataFrame:
    """Carrega o histórico consolidado do disco local."""
    os.makedirs(DIR_HISTORICO, exist_ok=True)
    if not os.path.exists(ARQUIVO_HISTORICO):
        return pd.DataFrame()
    try:
        return pd.read_parquet(ARQUIVO_HISTORICO)
    except Exception as e:
        print(f"[storage] ⚠️  Erro ao carregar histórico: {e}")
        return pd.DataFrame()

def salvar_historico(df: pd.DataFrame) -> None:
    """Salva o histórico consolidado no disco local."""
    os.makedirs(DIR_HISTORICO, exist_ok=True)
    try:
        df.to_parquet(ARQUIVO_HISTORICO, index=False)
        print(f"[storage] ✅ Histórico salvo: {len(df)} registros → {ARQUIVO_HISTORICO}")
    except Exception as e:
        print(f"[storage] ❌ Erro ao salvar histórico: {e}")
        raise
