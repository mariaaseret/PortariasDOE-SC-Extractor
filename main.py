# ==========================================
# Este script realiza a coleta automática de portarias publicadas no Diário Oficial de SC
# para o tema "calculados sobre a média das contribuições".
#
# Fluxo geral:
# 1️⃣ Busca as matérias usando a API:
#     https://portal.doe.sea.sc.gov.br/apis/materia/materia?ano=2025&mes=7&dataInicio=&dataFim=&assunto=35&categoria=4704302&dsMateria=calculados%20sobre%20a%20m%C3%A9dia%20das%20contribui%C3%A7%C3%B5es&tipoBusca=1&sortEdicao=&numeroEdicao=&numeroMateria=&ondePesquisar=4
#
# 2️⃣ Para cada resultado, chama:
#     https://portal.doe.sea.sc.gov.br/apis/edicao-preview/extrato/edicao/4099/materia/1094369
#     Este link retorna a URL final para o PDF específico daquela matéria.
#
# 3️⃣ Baixa o PDF, extrai os dados (nome do servidor, matrícula, cargo, órgão).
# 4️⃣ Gera uma planilha Excel com os resultados.
# ==========================================

!pip install requests pandas pdfplumber tqdm

import requests
import pandas as pd
import pdfplumber
from tqdm import tqdm
import re

# Período a buscar
anos = range(2025, 2026)
meses = range(1, 13)

BASE_URL = "https://portal.doe.sea.sc.gov.br"
API_MATERIA = BASE_URL + "/apis/materia/materia"
API_PDF_JSON = BASE_URL + "/apis/edicao-preview/extrato/edicao/{}/materia/{}"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

dados = []

print("🔎 Buscando matérias…")

# === Etapa 1: Consulta à API para listar as matérias ===
for ano in anos:
    for mes in meses:
        params = {
            "ano": ano,
            "mes": mes,
            "assunto": "35",
            "categoria": "4704302",
            "dsMateria": "calculados sobre a média das contribuições",
            "tipoBusca": "1",
            "ondePesquisar": "4"
        }
        resp = requests.get(API_MATERIA, params=params, headers=HEADERS)
        if resp.ok:
            lista = resp.json()
            if isinstance(lista, list):
                for item in lista:
                    dados.append(item)

print(f"✅ {len(dados)} matérias encontradas")

# === Etapa 2: Para cada matéria, pega a URL real do PDF ===
def obter_pdf_url(cdJornal, cdMateria):
    url_json = API_PDF_JSON.format(cdJornal, cdMateria)
    resp = requests.get(url_json, headers=HEADERS)
    if not resp.ok:
        return None
    json_resp = resp.json()
    return json_resp.get("urlExtratoArquivo")

# === Etapa 3: Processa o PDF e extrai os campos ===
def extrair_detalhes_pdf(url_pdf):
    resp = requests.get(url_pdf, headers=HEADERS)
    if not resp.ok:
        return None

    with open("/tmp/materia.pdf", "wb") as f:
        f.write(resp.content)

    with pdfplumber.open("/tmp/materia.pdf") as pdf:
        texto = ""
        for page in pdf.pages:
            texto += page.extract_text() + "\n"

    # Limpa quebras de linha e espaços excessivos
    texto_limpo = re.sub(r'\s+', ' ', texto)

    # Nome do servidor: trecho entre o último ' a ' e ', matrícula'
    try:
        idx_matricula = texto_limpo.lower().find(", matrícula")
        texto_ate_matricula = texto_limpo[:idx_matricula]
        idx_a = texto_ate_matricula.rfind(" a ")
        nome = texto_ate_matricula[idx_a+3:].strip() if idx_a != -1 else ""
    except:
        nome = ""

    # Matrícula
    try:
        match_matricula = re.search(r'matrícula\s+([0-9\-]+)', texto_limpo, flags=re.IGNORECASE)
        matricula = match_matricula.group(1).strip() if match_matricula else ""
    except:
        matricula = ""

    # Cargo
    try:
        cargo = texto_limpo.split("no cargo de")[-1].split(",")[0].strip()
    except:
        cargo = ""

    # Órgão
    try:
        orgao = texto_limpo.split("lotado(a) na")[-1].split(",")[0].strip()
    except:
        orgao = ""

    return nome, matricula, cargo, orgao

# === Etapa 4: Processa todas as matérias e coleta resultados ===
resultados = []
for item in tqdm(dados, desc="📄 Processando matérias"):
    url_pdf = obter_pdf_url(item["cdJornal"], item["cd_materia"])
    if url_pdf:
        res = extrair_detalhes_pdf(url_pdf)
    else:
        res = None

    if res:
        nome, matricula, cargo, orgao = res
    else:
        nome = matricula = cargo = orgao = ""

    resultados.append({
        "Nome do Servidor": nome,
        "Matrícula": matricula,
        "Cargo": cargo,
        "Órgão de Origem": orgao,
        "Data de Publicação do DOE": item["dtPublicacaoJornal"][:10],
        "Número da Edição do DOE": item["vlNumero"],
        "Número da Portaria": item["ds_titulo"].split("-")[0].strip(),
        "Data da Portaria": item["ds_titulo"].split("-")[1].split(".")[0].strip() if "-" in item["ds_titulo"] else ""
    })

# Converte para DataFrame
df_final = pd.DataFrame(resultados)

# === Etapa 5: Salva Excel ===
df_final.to_excel("portarias_doe.xlsx", index=False)
print("📁 Arquivo Excel gerado: portarias_doe.xlsx")

from google.colab import files
files.download("portarias_doe.xlsx")
