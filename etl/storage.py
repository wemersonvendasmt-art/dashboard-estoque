# etl/storage.py — versão local (sem Supabase, sem Google Drive)
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
