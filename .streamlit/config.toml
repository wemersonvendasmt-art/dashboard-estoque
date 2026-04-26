# etl/processar.py
import os
import pandas as pd
from config import (
    CSV_SEPARADOR, CSV_ENCODING, PULAR_LINHA_TOTAIS,
    DIAS_CRITICO, MAPA_COLUNAS,
    DIR_UPLOADS, DIR_HISTORICO,
    ARQUIVO_HISTORICO, ARQUIVO_FILIAIS,
    ARQUIVO_DEPTOS, ARQUIVO_PRODUTOS,
    ARQUIVO_PROCESSADOS
)
from utils import (
    limpar_numero, limpar_data,
    extrair_codigo_descricao, extrair_info_filename
)

# ─────────────────────────────────────────────────────────────────────────────
# 1. CARREGAR DIMENSÕES
# ─────────────────────────────────────────────────────────────────────────────

def carregar_dimensoes():
    """Carrega tabelas de dimensão para enriquecer os dados."""
    
    dim_filiais = pd.read_csv(ARQUIVO_FILIAIS, dtype=str)
    dim_filiais["nome_arquivo"] = dim_filiais["nome_arquivo"].str.upper().str.strip()
    
    dim_produtos = None
    if os.path.exists(ARQUIVO_PRODUTOS):
        dim_produtos = pd.read_csv(ARQUIVO_PRODUTOS, dtype=str)
        dim_produtos["codigo_sku"] = dim_produtos["codigo_sku"].str.strip()
    
    return dim_filiais, dim_produtos

# ─────────────────────────────────────────────────────────────────────────────
# 2. LER UM CSV DO QLIKVIEW
# ─────────────────────────────────────────────────────────────────────────────

def ler_csv_qlikview(caminho_arquivo, nome_arquivo):
    """
    Lê um CSV exportado do QlikView e retorna DataFrame limpo.
    """
    depto, filial_key, data_arquivo = extrair_info_filename(nome_arquivo)
    
    if depto is None:
        print(f"  ⚠️  Nome de arquivo fora do padrão: {nome_arquivo} — IGNORADO")
        return None

    # ── Leitura bruta ─────────────────────────────────────────────────────────
    try:
        df_raw = pd.read_csv(
            caminho_arquivo,
            sep=CSV_SEPARADOR,
            encoding=CSV_ENCODING,
            dtype=str,
            header=0
        )
    except UnicodeDecodeError:
        # Fallback para latin-1 (alguns exports do QlikView)
        df_raw = pd.read_csv(
            caminho_arquivo,
            sep=CSV_SEPARADOR,
            encoding="latin-1",
            dtype=str,
            header=0
        )

    # ── Remover linha de totais (linha 0 após header) ─────────────────────────
    if PULAR_LINHA_TOTAIS and len(df_raw) > 0:
        df_raw = df_raw.iloc[1:].reset_index(drop=True)

    # ── Remover linhas completamente vazias ───────────────────────────────────
    df_raw = df_raw.dropna(how="all").reset_index(drop=True)

    # ── Detectar colunas de vendas mensais ────────────────────────────────────
    colunas_conhecidas = set(MAPA_COLUNAS.keys())
    colunas_vendas = [
        c for c in df_raw.columns
        if c not in colunas_conhecidas
        and c.strip() not in ("", " ")
        and not c.startswith("Unnamed")
    ]
    # Ordena: mais recente primeiro (ordem no CSV = M0, M1, M2)
    colunas_vendas = colunas_vendas[:3]  # Máximo 3 meses

    # ── Renomear colunas conhecidas ───────────────────────────────────────────
    df = df_raw.rename(columns=MAPA_COLUNAS)

    # ── Renomear colunas de vendas mensais ────────────────────────────────────
    mapa_vendas = {}
    nomes_meses = ["venda_m0", "venda_m1", "venda_m2"]
    for i, col in enumerate(colunas_vendas):
        if col in df.columns:
            mapa_vendas[col] = nomes_meses[i]
            # Guarda o nome original do mês para referência
    df = df.rename(columns=mapa_vendas)

    # Guardar labels dos meses (ex: "abr 2026", "mar 2026", "fev 2026")
    labels_meses = {nomes_meses[i]: colunas_vendas[i] for i in range(len(colunas_vendas))}

    # ── Filtrar apenas linhas com produto válido ──────────────────────────────
    if "sku_raw" in df.columns:
        df = df[df["sku_raw"].notna() & (df["sku_raw"].str.strip() != "")]
    else:
        print(f"  ⚠️  Coluna 'Produto' não encontrada em {nome_arquivo}")
        return None

    # ── Extrair código e descrição ────────────────────────────────────────────
    df[["codigo_sku", "descricao"]] = df["sku_raw"].apply(
        lambda x: pd.Series(extrair_codigo_descricao(x))
    )

    # ── Limpar campos numéricos ───────────────────────────────────────────────
    campos_numericos = [
        "saldo", "giro", "dias_estoque",
        "valor_custo", "custo_unitario",
        "valor_venda", "mkp_pct", "preco_venda",
        "venda_m0", "venda_m1", "venda_m2"
    ]
    for campo in campos_numericos:
        if campo in df.columns:
            df[campo] = df[campo].apply(limpar_numero)

    # ── Limpar datas ──────────────────────────────────────────────────────────
    for campo_data in ["ultima_venda", "ultima_entrada"]:
        if campo_data in df.columns:
            df[campo_data] = df[campo_data].apply(limpar_data)

    # ── Adicionar metadados ───────────────────────────────────────────────────
    df["departamento"]  = depto
    df["filial_key"]    = filial_key.upper()
    df["data_arquivo"]  = data_arquivo
    df["nome_arquivo"]  = nome_arquivo

    # ── Calcular campo crítico ────────────────────────────────────────────────
    df["critico"] = df["dias_estoque"].apply(
        lambda x: True if (x is not None and x >= DIAS_CRITICO) else False
    )

    # ── Calcular dias desde última venda (para ranking de recuperação) ────────
    if "ultima_venda" in df.columns:
        df["dias_sem_venda"] = (data_arquivo - df["ultima_venda"]).dt.days

    # ── Selecionar e ordenar colunas finais ───────────────────────────────────
    colunas_finais = [
        "data_arquivo", "departamento", "filial_key",
        "codigo_sku", "descricao",
        "ultima_venda", "ultima_entrada",
        "saldo", "giro", "dias_estoque", "dias_sem_venda",
        "valor_custo", "custo_unitario",
        "valor_venda", "mkp_pct", "preco_venda",
        "venda_m0", "venda_m1", "venda_m2",
        "critico", "nome_arquivo"
    ]
    # Manter apenas colunas que existem
    colunas_finais = [c for c in colunas_finais if c in df.columns]
    df = df[colunas_finais]

    return df

# ─────────────────────────────────────────────────────────────────────────────
# 3. CARREGAR HISTÓRICO EXISTENTE
# ─────────────────────────────────────────────────────────────────────────────

def carregar_historico():
    """Carrega o histórico consolidado (parquet) se existir."""
    if os.path.exists(ARQUIVO_HISTORICO):
        return pd.read_parquet(ARQUIVO_HISTORICO)
    return pd.DataFrame()

def carregar_processados():
    """Retorna set com nomes de arquivos já processados."""
    if os.path.exists(ARQUIVO_PROCESSADOS):
        with open(ARQUIVO_PROCESSADOS, "r") as f:
            return set(line.strip() for line in f.readlines())
    return set()

def registrar_processado(nome_arquivo):
    """Registra arquivo como processado."""
    with open(ARQUIVO_PROCESSADOS, "a") as f:
        f.write(nome_arquivo + "\n")

# ─────────────────────────────────────────────────────────────────────────────
# 4. ENRIQUECER COM DIMENSÕES
# ─────────────────────────────────────────────────────────────────────────────

def enriquecer(df, dim_filiais, dim_produtos):
    """Faz JOIN com dimensões para adicionar estado, fornecedor, etc."""
    
    # JOIN com filiais → estado, nome_exibicao
    df = df.merge(
        dim_filiais[["nome_arquivo", "nome_exibicao", "estado", "uf"]],
        left_on="filial_key",
        right_on="nome_arquivo",
        how="left"
    )
    df = df.rename(columns={"nome_exibicao": "filial_nome"})
    df = df.drop(columns=["nome_arquivo_y"], errors="ignore")
    df = df.rename(columns={"nome_arquivo_x": "nome_arquivo"}, errors="ignore")

    # Fallback: se filial não mapeada, usar filial_key
    df["filial_nome"] = df["filial_nome"].fillna(df["filial_key"])
    df["estado"]      = df["estado"].fillna("Não mapeado")
    df["uf"]          = df["uf"].fillna("??")

    # JOIN com produtos → fornecedor, marca, categoria (opcional)
    if dim_produtos is not None and "codigo_sku" in df.columns:
        df = df.merge(
            dim_produtos,
            on="codigo_sku",
            how="left"
        )
        for col in ["fornecedor", "marca", "categoria", "subcategoria"]:
            if col not in df.columns:
                df[col] = "Não informado"
            else:
                df[col] = df[col].fillna("Não informado")
    else:
        df["fornecedor"]   = "Não informado"
        df["marca"]        = "Não informado"
        df["categoria"]    = "Não informado"
        df["subcategoria"] = "Não informado"

    return df

# ─────────────────────────────────────────────────────────────────────────────
# 5. PROCESSAR NOVOS ARQUIVOS
# ─────────────────────────────────────────────────────────────────────────────

def processar_novos():
    """
    Função principal:
    1. Varre pasta uploads/
    2. Processa apenas arquivos novos (não processados antes)
    3. Adiciona ao histórico consolidado
    4. Salva histórico atualizado
    """
    print("\n" + "="*60)
    print("  ETL — Dashboard de Estoque")
    print("="*60)

    # Carregar dimensões
    dim_filiais, dim_produtos = carregar_dimensoes()
    print(f"  ✅ Dimensões carregadas: {len(dim_filiais)} filiais mapeadas")

    # Listar arquivos na pasta uploads
    arquivos_disponiveis = [
        f for f in os.listdir(DIR_UPLOADS)
        if f.upper().endswith(".CSV")
    ]
    
    if not arquivos_disponiveis:
        print("  ℹ️  Nenhum CSV encontrado em dados/uploads/")
        return

    # Filtrar apenas novos
    ja_processados = carregar_processados()
    novos = [f for f in arquivos_disponiveis if f not in ja_processados]

    print(f"  📁 Arquivos em uploads/: {len(arquivos_disponiveis)}")
    print(f"  🔄 Já processados: {len(ja_processados)}")
    print(f"  🆕 Novos para processar: {len(novos)}")

    if not novos:
        print("  ✅ Nada novo para processar. Histórico está atualizado!")
        return

    # Carregar histórico existente
    historico = carregar_historico()
    novos_registros = []

    for nome_arquivo in sorted(novos):
        caminho = os.path.join(DIR_UPLOADS, nome_arquivo)
        print(f"\n  📄 Processando: {nome_arquivo}")
        
        try:
            df_novo = ler_csv_qlikview(caminho, nome_arquivo)
            
            if df_novo is None or df_novo.empty:
                print(f"     ⚠️  Arquivo vazio ou inválido — pulando")
                continue

            df_novo = enriquecer(df_novo, dim_filiais, dim_produtos)
            novos_registros.append(df_novo)
            registrar_processado(nome_arquivo)
            print(f"     ✅ {len(df_novo)} produtos carregados")

        except Exception as e:
            print(f"     ❌ ERRO ao processar {nome_arquivo}: {e}")
            continue

    # Consolidar e salvar
    if novos_registros:
        df_novos_concat = pd.concat(novos_registros, ignore_index=True)
        
        if not historico.empty:
            historico_final = pd.concat(
                [historico, df_novos_concat], ignore_index=True
            )
        else:
            historico_final = df_novos_concat

        # Remover duplicatas (mesmo arquivo processado duas vezes por engano)
        historico_final = historico_final.drop_duplicates(
            subset=["data_arquivo", "departamento", "filial_key", "codigo_sku"],
            keep="last"
        )

        # Garantir tipos corretos antes de salvar
        historico_final["data_arquivo"] = pd.to_datetime(
            historico_final["data_arquivo"], errors="coerce"
        )

        # Salvar em parquet (eficiente para grandes volumes)
        os.makedirs(DIR_HISTORICO, exist_ok=True)
        historico_final.to_parquet(ARQUIVO_HISTORICO, index=False)

        print(f"\n  💾 Histórico salvo: {len(historico_final):,} registros totais")
        print(f"  📅 Período: {historico_final['data_arquivo'].min().date()} "
              f"até {historico_final['data_arquivo'].max().date()}")
    
    print("\n" + "="*60)
    print("  ETL concluído com sucesso!")
    print("="*60 + "\n")

# ─────────────────────────────────────────────────────────────────────────────
# EXECUÇÃO DIRETA
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    processar_novos()
