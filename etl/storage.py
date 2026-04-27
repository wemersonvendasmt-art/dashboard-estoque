# etl/storage.py
import os
import pandas as pd
from config import ARQUIVO_HISTORICO, DIR_HISTORICO

def carregar_historico() -> pd.DataFrame:
    """Carrega o histórico consolidado do disco local."""
    if not os.path.exists(ARQUIVO_HISTORICO):
        return pd.DataFrame()
    try:
        df = pd.read_parquet(ARQUIVO_HISTORICO)
        df["data_arquivo"] = pd.to_datetime(df["data_arquivo"], errors="coerce")
        return df
    except Exception as e:
        print(f"[storage] ⚠️ Erro ao carregar histórico: {e}")
        return pd.DataFrame()

def salvar_historico(df: pd.DataFrame):
    """Salva o histórico consolidado em parquet local."""
    os.makedirs(DIR_HISTORICO, exist_ok=True)
    try:
        df.to_parquet(ARQUIVO_HISTORICO, index=False)
        print(f"[storage] ✅ Histórico salvo: {len(df)} linhas → {ARQUIVO_HISTORICO}")
    except Exception as e:
        print(f"[storage] ❌ Erro ao salvar histórico: {e}")
        raise
