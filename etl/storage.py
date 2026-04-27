# etl/storage.py
import os
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
import io
import pandas as pd

BUCKET_NAME   = "historico"
ARQUIVO_NOME  = "historico.parquet"

def _cliente():
    from supabase import create_client
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)

def carregar_historico() -> pd.DataFrame:
    """Baixa o parquet do Supabase Storage e retorna DataFrame."""
    try:
        sb   = _cliente()
        data = sb.storage.from_(BUCKET_NAME).download(ARQUIVO_NOME)
        df   = pd.read_parquet(io.BytesIO(data))
        print(f"[storage] ✅ Histórico carregado: {len(df)} linhas")
        return df
    except Exception as e:
        msg = str(e)
        if "Object not found" in msg or "404" in msg or "does not exist" in msg:
            print("[storage] ℹ️  Histórico ainda não existe — iniciando vazio.")
        else:
            print(f"[storage] ⚠️  Erro ao carregar histórico: {e}")
        return pd.DataFrame()

def salvar_historico(df: pd.DataFrame):
    """Serializa DataFrame para parquet e faz upload no Supabase Storage."""
    try:
        sb     = _cliente()
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False, engine="pyarrow")
        buffer.seek(0)
        conteudo = buffer.read()

        # Tenta upsert (update se existe, insert se não existe)
        try:
            sb.storage.from_(BUCKET_NAME).update(
                ARQUIVO_NOME,
                conteudo,
                {"content-type": "application/octet-stream"}
            )
        except Exception:
            sb.storage.from_(BUCKET_NAME).upload(
                ARQUIVO_NOME,
                conteudo,
                {"content-type": "application/octet-stream"}
            )

        print(f"[storage] ✅ Histórico salvo: {len(df)} linhas")
    except Exception as e:
        print(f"[storage] ❌ Erro ao salvar histórico: {e}")
        raise
