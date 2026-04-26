# 📦 Dashboard de Estoque — Compras

Dashboard web 100% gratuito para acompanhamento de estoque parado,
itens críticos (+90 dias), ranking de filiais, fornecedores e departamentos.

## 🏪 Filiais cobertas
| Filial | Estado |
|---|---|
| Canaã | AL |
| Expedicionário | AL |
| Olho D'Água das Flores | AL |
| Jatiúca - Maceió | AL |
| Catedral | AL |
| Delmiro Gouveia | AL |
| 15 de Novembro | AL |
| Aracaju | SE |
| Lagarto | SE |
| Umbaúba | SE |
| Paripiranga | BA |

## 📂 Departamentos
- AGRO
- PECUARIA
- PET
- CASAJARDIM
- MAQUINAS

---

## 🚀 Como acessar o dashboard (equipe e diretores)

Acesse pelo link do Streamlit Cloud (gerado após o deploy):
```
https://seu-usuario.streamlit.app/dashboard/app
```
> O link será fixo e pode ser salvo como favorito no celular ou computador.

---

## 📤 Rotina diária — Como subir os arquivos

### Passo a passo (5 minutos por dia)

1. Exporte os CSVs do QlikView normalmente
2. **Renomeie** cada arquivo seguindo o padrão:
   ```
   GIRO-{DEPTO}-FILIAL-{FILIAL}-{DD}-{MM}-{AA}.csv
   ```
   Exemplos:
   ```
   GIRO-PET-FILIAL-CATEDRAL-26-04-26.csv
   GIRO-AGRO-FILIAL-ARACAJU-26-04-26.csv
   GIRO-PECUARIA-FILIAL-JATIUCA-26-04-26.csv
   GIRO-CASAJARDIM-FILIAL-CANAA-26-04-26.csv
   GIRO-MAQUINAS-FILIAL-LAGARTO-26-04-26.csv
   ```

3. Acesse o dashboard pelo link
4. No painel **lateral esquerdo**, clique em **"Arraste os CSVs aqui"**
5. Selecione todos os arquivos do dia (até 55 de uma vez)
6. Clique em **"▶️ Processar agora"**
7. Aguarde a mensagem ✅ — o dashboard atualiza automaticamente

> ⚠️ Não precisa instalar nada. Tudo funciona pelo navegador.

---

## 🛠️ Como fazer o deploy (uma vez só — 20 minutos)

### Pré-requisitos
- Conta no [GitHub](https://github.com) (gratuita)
- Conta no [Streamlit Cloud](https://streamlit.io/cloud) (gratuita — login com GitHub)

### Passo 1 — Criar o repositório no GitHub

1. Acesse [github.com](https://github.com) e faça login
2. Clique em **"New repository"**
3. Nome: `dashboard-estoque`
4. Marque **"Private"** (repositório privado — seus dados ficam protegidos)
5. Clique em **"Create repository"**

### Passo 2 — Subir os arquivos pelo browser

> Você não precisa instalar Git. Tudo pelo browser.

1. No repositório criado, clique em **"uploading an existing file"**
2. Suba os arquivos **um por um** ou em grupos:

**Ordem recomendada:**

```
Primeiro suba:
├── requirements.txt
├── packages.txt
├── .gitignore
├── README.md

Depois crie as pastas e suba:
├── .streamlit/
│   └── config.toml
├── etl/
│   ├── config.py
│   ├── utils.py
│   └── processar.py
├── dashboard/
│   ├── app.py
│   ├── componentes/
│   │   ├── __init__.py   ← arquivo vazio
│   │   └── kpis.py
│   └── paginas/
│       ├── __init__.py   ← arquivo vazio
│       ├── visao_geral.py
│       ├── filiais.py
│       ├── fornecedores.py
│       ├── departamentos.py
│       ├── produtos_criticos.py
│       └── evolucao.py
└── dados/
    ├── uploads/
    │   └── .gitkeep      ← arquivo vazio com este nome exato
    ├── historico/
    │   └── .gitkeep      ← arquivo vazio com este nome exato
    └── dimensoes/
        ├── dim_filiais.csv
        ├── dim_deptos.csv
        └── dim_produtos.csv
```

> 💡 **Como criar pasta no GitHub pelo browser:**
> Ao subir um arquivo, no campo de nome digite:
> `dashboard/paginas/visao_geral.py`
> O GitHub cria as pastas automaticamente.

### Passo 3 — Conectar ao Streamlit Cloud

1. Acesse [share.streamlit.io](https://share.streamlit.io)
2. Clique em **"New app"**
3. Preencha:
   - **Repository:** `seu-usuario/dashboard-estoque`
   - **Branch:** `main`
   - **Main file path:** `dashboard/app.py`
4. Clique em **"Deploy!"**
5. Aguarde ~3 minutos — o link estará disponível

### Passo 4 — Compartilhar o link

- Copie o link gerado (ex: `https://dashboard-estoque.streamlit.app`)
- Envie para a equipe de compras e diretores
- O link é permanente e gratuito

---

## 🔒 Segurança e boas práticas

### O que NÃO vai para o GitHub (protegido pelo .gitignore)
```
dados/uploads/*.csv     ← CSVs com dados da empresa
dados/historico/*.csv   ← Histórico consolidado
dados/historico/*.parquet
```

### Como os dados ficam armazenados
- Os CSVs são processados e armazenados **dentro do Streamlit Cloud**
- O histórico fica em `dados/historico/historico_consolidado.parquet`
- **Atenção:** O Streamlit Cloud gratuito reinicia o servidor periodicamente.
  Para persistência permanente, use a solução de backup abaixo.

### Solução de backup do histórico (recomendado)

Adicione ao `etl/config.py` após o deploy:
```python
# Usar GitHub como backup do histórico
# Suba manualmente o historico_consolidado.parquet para o repositório
# uma vez por semana como backup
```

---

## 📁 Estrutura do repositório

```
dashboard-estoque/
│
├── README.md
├── .gitignore
├── requirements.txt
├── packages.txt
│
├── .streamlit/
│   └── config.toml
│
├── dados/
│   ├── uploads/         ← CSVs diários (não vão para o GitHub)
│   ├── historico/       ← Parquet consolidado (não vai para o GitHub)
│   └── dimensoes/
│       ├── dim_filiais.csv
│       ├── dim_deptos.csv
│       └── dim_produtos.csv
│
├── etl/
│   ├── config.py
│   ├── utils.py
│   └── processar.py
│
└── dashboard/
    ├── app.py
    ├── componentes/
    │   ├── __init__.py
    │   └── kpis.py
    └── paginas/
        ├── __init__.py
        ├── visao_geral.py
        ├── filiais.py
        ├── fornecedores.py
        ├── departamentos.py
        ├── produtos_criticos.py
        └── evolucao.py
```

---

## ❓ Dúvidas frequentes

**O dashboard sumiu / perdeu os dados?**
> O Streamlit Cloud gratuito pode reiniciar. Basta subir os CSVs novamente.
> Para evitar isso, faça backup semanal do arquivo `historico_consolidado.parquet`.

**Posso usar no celular?**
> Sim! O Streamlit é responsivo. Funciona em qualquer navegador.

**Quantas pessoas podem acessar ao mesmo tempo?**
> No plano gratuito: sem limite de usuários, mas pode ficar lento com muitos acessos simultâneos.

**Como adicionar um novo departamento ou filial?**
> Edite os arquivos `dim_filiais.csv` e `dim_deptos.csv` diretamente no GitHub.

---

## 👥 Equipe

Projeto criado para o setor de **Compras**.
Dúvidas técnicas: fale com o responsável pelo repositório.
