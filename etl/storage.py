# etl/storage.py
import os
import io
import pickle
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2 import service_account

# ── Configuração ──────────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/drive"]
NOME_ARQUIVO_HISTORICO = "historico_estoque.parquet"

def _get_service():
    """Autentica via Service Account (variável de ambiente GOOGLE_CREDENTIALS_JSON)."""
    import json
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise EnvironmentError(
            "Variável GOOGLE_CREDENTIALS_JSON não encontrada. "
            "Configure no Render → Environment."
        )
    creds_info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        creds_info, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)

def _get_folder_id():
    """Retorna o ID da pasta no Google Drive (variável GDRIVE_FOLDER_ID)."""
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")
    if not folder_id:
        raise EnvironmentError(
            "Variável GDRIVE_FOLDER_ID não encontrada. "
            "Configure no Render → Environment."
        )
    return folder_id

def _buscar_arquivo(service, nome, folder_id):
    """Retorna o fileId de um arquivo pelo nome dentro da pasta."""
    query = (
        f"name='{nome}' and '{folder_id}' in parents "
        f"and trashed=false"
    )
    resultado = service.files().list(
        q=query, spaces="drive", fields="files(id, name)"
    ).execute()
    arquivos = resultado.get("files", [])
    return arquivos[0]["id"] if arquivos else None

def carregar_historico():
    """
    Baixa o histórico consolidado do Google Drive e retorna como DataFrame.
    Retorna DataFrame vazio se o arquivo ainda não existir.
    """
    try:
        service   = _get_service()
        folder_id = _get_folder_id()
        file_id   = _buscar_arquivo(service, NOME_ARQUIVO_HISTORICO, folder_id)

        if file_id is None:
            return pd.DataFrame()

        buffer = io.BytesIO()
        request = service.files().get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        buffer.seek(0)
        return pd.read_parquet(buffer)

    except Exception as e:
        print(f"[storage] Erro ao carregar histórico: {e}")
        return pd.DataFrame()

def salvar_historico(df: pd.DataFrame):
    """
    Salva o DataFrame como parquet no Google Drive.
    Substitui o arquivo existente se já houver um.
    """
    try:
        service   = _get_service()
        folder_id = _get_folder_id()
        file_id   = _buscar_arquivo(service, NOME_ARQUIVO_HISTORICO, folder_id)

        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False, engine="pyarrow")
        buffer.seek(0)

        media = MediaIoBaseUpload(
            buffer,
            mimetype="application/octet-stream",
            resumable=True
        )

        if file_id:
            # Atualiza arquivo existente
            service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
        else:
            # Cria novo arquivo
            metadata = {
                "name": NOME_ARQUIVO_HISTORICO,
                "parents": [folder_id]
            }
            service.files().create(
                body=metadata,
                media_body=media,
                fields="id"
            ).execute()

        print(f"[storage] Histórico salvo com sucesso ({len(df)} registros).")

    except Exception as e:
        print(f"[storage] Erro ao salvar histórico: {e}")
        raise
