@st.cache_data(ttl=300)
def carregar_dados():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "etl"))
    import storage
    df = storage.carregar_historico()
    if not df.empty:
        df["data_arquivo"] = pd.to_datetime(df["data_arquivo"], errors="coerce")
    return df
