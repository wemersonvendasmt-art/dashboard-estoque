# etl/utils.py
import re
import pandas as pd

def limpar_numero(valor):
    """
    Converte string brasileira para float.
    Ex: '28.428,32' → 28428.32
        '46,20%'    → 46.20
        '-'         → None
    """
    if pd.isna(valor) or str(valor).strip() in ("-", "", "nan"):
        return None
    s = str(valor).strip()
    s = s.replace("%", "").strip()
    # Remove pontos de milhar, troca vírgula decimal por ponto
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

def limpar_data(valor):
    """
    Converte string de data para datetime.
    Aceita: '20/04/2026', '-', NaN
    """
    if pd.isna(valor) or str(valor).strip() in ("-", "", "nan"):
        return pd.NaT
    try:
        return pd.to_datetime(str(valor).strip(), format="%d/%m/%Y", errors="coerce")
    except Exception:
        return pd.NaT

def extrair_codigo_descricao(sku_raw):
    """
    '0017687 - PLANETA DOG CARNE AD 25KG'
    → codigo='0017687', descricao='PLANETA DOG CARNE AD 25KG'
    """
    if pd.isna(sku_raw) or str(sku_raw).strip() == "":
        return None, None
    partes = str(sku_raw).split(" - ", 1)
    codigo = partes[0].strip()
    descricao = partes[1].strip() if len(partes) > 1 else ""
    return codigo, descricao

def extrair_info_filename(nome_arquivo):
    """
    'GIRO-PET-FILIAL-CATEDRAL-25-04-26.csv'
    → depto='PET', filial='CATEDRAL', data=datetime(2026,4,25)

    Padrão: GIRO-{DEPTO}-FILIAL-{FILIAL}-{DD}-{MM}-{AA}.csv
    """
    nome = nome_arquivo.replace(".csv", "").replace(".CSV", "")
    # Regex: GIRO-DEPTO-FILIAL-NOME-DD-MM-AA
    padrao = r"^GIRO-([A-Z0-9]+)-FILIAL-([A-Z0-9]+)-(\d{2})-(\d{2})-(\d{2})$"
    m = re.match(padrao, nome.upper())
    if not m:
        return None, None, None
    depto  = m.group(1)
    filial = m.group(2)
    dd, mm, aa = int(m.group(3)), int(m.group(4)), int(m.group(5))
    ano = 2000 + aa
    try:
        data = pd.Timestamp(ano, mm, dd)
    except Exception:
        data = None
    return depto, filial, data
