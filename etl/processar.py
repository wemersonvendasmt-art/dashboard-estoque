# etl/processar.py
import os
import re
import pandas as pd
from config import DIR_UPLOADS
import storage

COLUNAS_MAP = {
    "Produto":         "sku_descricao",
    "Última Venda":    "ultima_venda",
    "Última Entrada":  "ultima_entrada",
    "Saldo":           "saldo",
    "Giro":            "giro",
    "Dias Est":        "dias_estoque",
    "Saldo Compra R$": "valor_custo",
    "UN Compra R$":    "custo_unitario",
    "Saldo Venda R$":  "valor_venda",
    "%MKP":            "mkp_pct",
    "UN Venda R$":     "preco_venda",
}

FILIAIS_MAP = {
    "CANAA":         {"nome": "Canaã",           "uf": "AL"},
    "EXPEDICIONARIO":{"nome": "Expedicionário",  "uf": "AL"},
    "OLHODAGUA":     {"nome": "Olho D'Água",     "uf": "AL"},
    "JATIUCA":       {"nome": "Jatiúca",         "uf": "AL"},
    "CATEDRAL":      {"nome": "Catedral",        "uf": "AL"},
    "ARACAJU":       {"nome": "Aracaju",         "uf": "SE"},
    "DELMIRO":       {"nome": "Delmiro Gouveia", "uf": "AL"},
    "15DENOVEMBRO":  {"nome": "15 de Novembro",  "uf": "AL"},
    "LAGARTO":       {"nome": "Lagarto",         "uf": "SE"},
    "UMBAUBA":       {"nome": "Umbaúba",         "uf": "SE"},
    "PARIPIRANGA":   {"nome": "Paripiranga",     "uf": "BA"},
}

# Colunas obrigatórias para o formato de GIRO (Formato A)
COLUNAS_GIRO_OBRIGATORIAS = {"Dias Est", "Saldo", "Giro"}

def _parsear_nome_arquivo(nome):
    padrao = r"GIRO-(.+?)-FILIAL-(.+?)-(\d{2})-(\d{2})-(\d{2})\.csv"
    m = re.match(padrao, nome, re.IGNORECASE)
    if not m:
        return None
    depto, filial, dd, mm, aa = m.groups()
    data = pd.Timestamp(f"20{aa}-{mm}-{dd}")
    return {
        "departamento": depto.upper(),
        "filial_key":   filial.upper(),
        "data_arquivo": data,
    }

def _detectar_formato(df_raw):
    """
    Retorna 'GIRO' se o CSV tem as colunas de giro esperadas,
    ou 'DISTRIBUICAO' se for o formato de transferência entre filiais.
    """
    colunas = set(df_raw.columns)
    if COLUNAS_GIRO_OBRIGATORIAS.issubset(colunas):
        return "GIRO"
    # Formato distribuição: tem coluna "Produto - Descricao" e colunas de filiais
    if any("Produto" in c for c in colunas) and "Total" in colunas:
        return "DISTRIBUICAO"
    return "DESCONHECIDO"

def _ler_csv(caminho):
    """Tenta ler o CSV com diferentes encodings/separadores."""
    for sep, enc in [(";", "latin-1"), (";", "utf-8"), (",", "utf-8")]:
        try:
            df = pd.read_csv(caminho, sep=sep, encoding=enc, decimal=",")
            if len(df.columns) > 2:
                return df
        except Exception:
            continue
    return None

def _processar_csv_giro(df, meta):
    """Processa CSV no Formato A (giro diário por filial)."""
    # Renomear colunas conhecidas
    df = df.rename(columns={
        k: v for k, v in COLUNAS_MAP.items() if k in df.columns
    })

    # Detectar colunas de venda mensal (ex: "abr 2026")
    colunas_venda = [c for c in df.columns if re.match(r"[a-z]{3} \d{4}", c, re.I)]
    for i, col in enumerate(sorted(colunas_venda, reverse=True)):
        df[f"venda_m{i}"] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "."), errors="coerce"
        )

    # Extrair código e descrição do SKU
    if "sku_descricao" in df.columns:
        df["codigo_sku"] = df["sku_descricao"].str.extract(r"^(\d+)")
        df["descricao"]  = df["sku_descricao"].str.replace(
            r"^\d+\s*-\s*", "", regex=True
        )

    # Converter tipos numéricos
    for col in ["saldo", "giro", "dias_estoque", "valor_custo",
                "custo_unitario", "valor_venda", "mkp_pct", "preco_venda"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "."), errors="coerce"
            )

    # Converter datas
    for col in ["ultima_venda", "ultima_entrada"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")

    # Garantir que dias_estoque existe (fallback = 0)
    if "dias_estoque" not in df.columns:
        df["dias_estoque"] = 0

    # Metadados
    filial_info = FILIAIS_MAP.get(meta["filial_key"], {
        "nome": meta["filial_key"], "uf": "??"
    })
    df["filial_key"]   = meta["filial_key"]
    df["filial_nome"]  = filial_info["nome"]
    df["uf"]           = filial_info["uf"]
    df["departamento"] = meta["departamento"]
    df["data_arquivo"] = meta["data_arquivo"]
    df["formato"]      = "GIRO"

    # Flag crítico
    df["critico"] = df["dias_estoque"].fillna(0) >= 90

    # Remover linhas sem SKU (totalizadores)
    df = df[df["codigo_sku"].notna()]

    return df

def _processar_csv_distribuicao(df, meta):
    """
    Processa CSV no Formato B (distribuição/sugestão de transferência).
    Retorna None — este formato não alimenta o histórico de giro,
    mas pode ser salvo separadamente no futuro.
    """
    print(f"[processar] ℹ️  Formato DISTRIBUIÇÃO detectado — ignorado para histórico: {meta['filial_key']}")
    return None

def processar_novos():
    """
    Lê todos os CSVs em DIR_UPLOADS, detecta o formato,
    processa apenas os de GIRO e consolida com o histórico.
    """
    arquivos = [
        f for f in os.listdir(DIR_UPLOADS)
        if f.lower().endswith(".csv")
    ]

    if not arquivos:
        print("[processar] Nenhum CSV encontrado em uploads/")
        return 0

    df_historico = storage.carregar_historico()
    novos_frames = []
    processados  = 0
    ignorados    = 0

    for nome in arquivos:
        meta = _parsear_nome_arquivo(nome)
        if meta is None:
            print(f"[processar] ⚠️  Nome inválido, ignorado: {nome}")
            continue

        caminho = os.path.join(DIR_UPLOADS, nome)
        df_raw  = _ler_csv(caminho)

        if df_raw is None:
            print(f"[processar] ❌ Não foi possível ler: {nome}")
            continue

        formato = _detectar_formato(df_raw)

        if formato == "GIRO":
            df_novo = _processar_csv_giro(df_raw, meta)
            if df_novo is None or df_novo.empty:
                print(f"[processar] ⚠️  Vazio após processar: {nome}")
                continue

            # Remover registros da mesma data+filial+depto do histórico
            if not df_historico.empty:
                mask = ~(
                    (df_historico["data_arquivo"] == meta["data_arquivo"]) &
                    (df_historico["filial_key"]   == meta["filial_key"])   &
                    (df_historico["departamento"] == meta["departamento"])
                )
                df_historico = df_historico[mask]

            novos_frames.append(df_novo)
            processados += 1
            print(f"[processar] ✓ {nome} ({len(df_novo)} linhas)")

        elif formato == "DISTRIBUICAO":
            _processar_csv_distribuicao(df_raw, meta)
            ignorados += 1

        else:
            print(f"[processar] ❓ Formato desconhecido, ignorado: {nome}")
            ignorados += 1

    if novos_frames:
        df_consolidado = pd.concat(
            [df_historico] + novos_frames,
            ignore_index=True
        )
        storage.salvar_historico(df_consolidado)

    # Limpar uploads após processar
    for nome in arquivos:
        try:
            os.remove(os.path.join(DIR_UPLOADS, nome))
        except Exception:
            pass

    print(f"[processar] Concluído: {processados} processados, {ignorados} ignorados")
    return processados
