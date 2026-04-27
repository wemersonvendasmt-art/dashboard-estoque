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
    "CANAA":          {"nome": "Canaã",           "uf": "AL"},
    "EXPEDICIONARIO": {"nome": "Expedicionário",  "uf": "AL"},
    "OLHODAGUA":      {"nome": "Olho D'Água",     "uf": "AL"},
    "JATIUCA":        {"nome": "Jatiúca",         "uf": "AL"},
    "CATEDRAL":       {"nome": "Catedral",        "uf": "AL"},
    "ARACAJU":        {"nome": "Aracaju",         "uf": "SE"},
    "DELMIRO":        {"nome": "Delmiro Gouveia", "uf": "AL"},
    "15DENOVEMBRO":   {"nome": "15 de Novembro",  "uf": "AL"},
    "LAGARTO":        {"nome": "Lagarto",         "uf": "SE"},
    "UMBAUBA":        {"nome": "Umbaúba",         "uf": "SE"},
    "PARIPIRANGA":    {"nome": "Paripiranga",     "uf": "BA"},
}

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
    colunas = set(df_raw.columns)
    if COLUNAS_GIRO_OBRIGATORIAS.issubset(colunas):
        return "GIRO"
    if any("Produto" in c for c in colunas) and "Total" in colunas:
        return "DISTRIBUICAO"
    return "DESCONHECIDO"

def _ler_csv(caminho):
    for sep, enc in [(";", "latin-1"), (";", "utf-8"), (",", "utf-8"), (",", "latin-1")]:
        try:
            df = pd.read_csv(caminho, sep=sep, encoding=enc, dtype=str)
            if len(df.columns) > 2:
                return df
        except Exception:
            continue
    return None

def _limpar_numero(serie):
    """Converte string com vírgula decimal para float. Ex: '1.234,56' → 1234.56"""
    return (
        serie.astype(str)
             .str.strip()
             .str.replace(r"\.", "", regex=True)   # remove separador de milhar
             .str.replace(",", ".", regex=False)    # vírgula → ponto decimal
             .pipe(pd.to_numeric, errors="coerce")
    )

def _processar_csv_giro(df, meta):
    # 1. Limpar nomes de colunas (BOM, espaços)
    df.columns = (
        df.columns
          .str.strip()
          .str.replace('\ufeff', '', regex=False)
          .str.replace('\u200b', '', regex=False)
    )

    # 2. Renomear colunas conhecidas
    df = df.rename(columns={
        k: v for k, v in COLUNAS_MAP.items() if k in df.columns
    })

    # 3. Detectar e processar colunas de venda mensal (ex: "abr 2026")
    colunas_venda = [
        c for c in df.columns
        if re.match(r"^[a-záéíóúâêîôûãõ]{3}\.?\s+\d{4}$", c.strip(), re.IGNORECASE)
    ]
    for i, col in enumerate(sorted(colunas_venda, reverse=True)):
        df[f"venda_m{i}"] = _limpar_numero(df[col])
    # Remover colunas originais de venda mensal (evita conflito de tipo no parquet)
    df = df.drop(columns=colunas_venda, errors="ignore")

    # 4. Extrair código e descrição do SKU
    if "sku_descricao" in df.columns:
        df["codigo_sku"] = df["sku_descricao"].astype(str).str.extract(r"^(\d+)")
        df["descricao"]  = df["sku_descricao"].astype(str).str.replace(
            r"^\d+\s*[-–]\s*", "", regex=True
        ).str.strip()
    else:
        col_produto = next(
            (c for c in df.columns if "produto" in c.lower()), None
        )
        if col_produto:
            df = df.rename(columns={col_produto: "sku_descricao"})
            df["codigo_sku"] = df["sku_descricao"].astype(str).str.extract(r"^(\d+)")
            df["descricao"]  = df["sku_descricao"].astype(str).str.replace(
                r"^\d+\s*[-–]\s*", "", regex=True
            ).str.strip()
        else:
            print(f"[processar] ⚠️  Coluna 'Produto' não encontrada. Colunas: {list(df.columns)}")
            df["codigo_sku"] = None
            df["descricao"]  = None

    # 5. Converter colunas numéricas
    for col in ["saldo", "giro", "dias_estoque", "valor_custo",
                "custo_unitario", "valor_venda", "mkp_pct", "preco_venda"]:
        if col in df.columns:
            df[col] = _limpar_numero(df[col])

    # 6. Converter colunas de data
    for col in ["ultima_venda", "ultima_entrada"]:
        if col in df.columns:
            df[col] = pd.to_datetime(
                df[col].astype(str).str.strip(),
                dayfirst=True, errors="coerce"
            )

    # 7. Garantir dias_estoque
    if "dias_estoque" not in df.columns:
        df["dias_estoque"] = 0.0
    df["dias_estoque"] = df["dias_estoque"].fillna(0)

    # 8. Metadados
    filial_info = FILIAIS_MAP.get(meta["filial_key"], {
        "nome": meta["filial_key"], "uf": "??"
    })
    df["filial_key"]   = meta["filial_key"]
    df["filial_nome"]  = filial_info["nome"]
    df["uf"]           = filial_info["uf"]
    df["departamento"] = meta["departamento"]
    df["data_arquivo"] = meta["data_arquivo"]
    df["formato"]      = "GIRO"

    # 9. Flag crítico
    df["critico"] = df["dias_estoque"] >= 90

    # 10. Remover linhas sem SKU (totalizadores/rodapé)
    df = df[df["codigo_sku"].notna()].copy()

    # 11. Garantir tipos corretos antes do parquet
    df = _garantir_tipos(df)

    return df

def _garantir_tipos(df):
    """
    Força tipos corretos em todas as colunas para evitar erro do pyarrow
    ao salvar parquet. Qualquer coluna object com números vira float64.
    """
    colunas_float = [
        "saldo", "giro", "dias_estoque", "valor_custo", "custo_unitario",
        "valor_venda", "mkp_pct", "preco_venda"
    ]
    # Colunas de venda mensal dinâmicas
    colunas_float += [c for c in df.columns if re.match(r"^venda_m\d+$", c)]

    for col in colunas_float:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    # Colunas string
    for col in ["codigo_sku", "descricao", "sku_descricao",
                "filial_key", "filial_nome", "uf",
                "departamento", "formato"]:
        if col in df.columns:
            df[col] = df[col].astype(str).where(df[col].notna(), other=None)

    # Bool
    if "critico" in df.columns:
        df["critico"] = df["critico"].astype(bool)

    # Datas
    for col in ["ultima_venda", "ultima_entrada", "data_arquivo"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df

def _processar_csv_distribuicao(df, meta):
    print(f"[processar] ℹ️  Formato DISTRIBUIÇÃO — ignorado: {meta['filial_key']}")
    return None

def processar_novos():
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
            ignorados += 1
            continue

        caminho = os.path.join(DIR_UPLOADS, nome)
        df_raw  = _ler_csv(caminho)

        if df_raw is None:
            print(f"[processar] ❌ Não foi possível ler: {nome}")
            ignorados += 1
            continue

        # Limpar nomes antes de detectar formato
        df_raw.columns = (
            df_raw.columns
                  .str.strip()
                  .str.replace('\ufeff', '', regex=False)
        )

        formato = _detectar_formato(df_raw)

        if formato == "GIRO":
            try:
                df_novo = _processar_csv_giro(df_raw, meta)
            except Exception as e:
                print(f"[processar] ❌ Erro ao processar {nome}: {e}")
                ignorados += 1
                continue

            if df_novo is None or df_novo.empty:
                print(f"[processar] ⚠️  Vazio após processar: {nome}")
                ignorados += 1
                continue

            # Remover registros duplicados do histórico
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
            print(f"[processar] ❓ Formato desconhecido: {nome}. Colunas: {list(df_raw.columns)}")
            ignorados += 1

    if novos_frames:
        df_consolidado = pd.concat(
            [df_historico] + novos_frames,
            ignore_index=True
        )
        try:
            storage.salvar_historico(df_consolidado)
            print(f"[processar] 💾 Histórico salvo: {len(df_consolidado)} linhas totais")
        except Exception as e:
            print(f"[processar] ❌ Erro ao salvar histórico: {e}")
            raise

    # Limpar uploads após processar
    for nome in arquivos:
        try:
            os.remove(os.path.join(DIR_UPLOADS, nome))
        except Exception:
            pass

    print(f"[processar] ✅ Concluído: {processados} processados, {ignorados} ignorados")
    return processados
