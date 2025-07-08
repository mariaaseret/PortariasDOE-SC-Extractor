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

anos = range(2025, 2026)
meses = range(1, 13)

BASE_URL = "https://portal.doe.sea.sc.gov.br"
API_MATERIA = BASE_URL + "/apis/materia/materia"
API_PDF_JSON = BASE_URL + "/apis/edicao-preview/extrato/edicao/{}/materia/{}"

HEADERS = {"User-Agent": "Mozilla/5.0"}

dados = []

print("🔎 Buscando matérias…")

# === Etapa 1: Consulta à API para listar as matérias ===
for ano in anos:
    for mes in meses:
        params = {
            "ano": ano, "mes": mes,
            "assunto": "35", "categoria": "4704302",
            "dsMateria": "calculados sobre a média das contribuições",
            "tipoBusca": "1", "ondePesquisar": "4"
        }
        resp = requests.get(API_MATERIA, params=params, headers=HEADERS)
        if resp.ok:
            lista = resp.json()
            if isinstance(lista, list):
                dados.extend(lista)

print(f"✅ {len(dados)} matérias encontradas")

# === Etapa 2: Para cada matéria, pega a URL real do PDF ===
def obter_pdf_url(cdJornal, cdMateria):
    url_json = API_PDF_JSON.format(cdJornal, cdMateria)
    resp = requests.get(url_json, headers=HEADERS)
    if not resp.ok:
        return None
    return resp.json().get("urlExtratoArquivo")

# === Etapa 3: Processa o PDF e devolve lista de registros válidos ===
def extrair_detalhes_pdf(url_pdf):
    resp = requests.get(url_pdf, headers=HEADERS)
    if not resp.ok:
        return []

    with open("/tmp/materia.pdf", "wb") as f:
        f.write(resp.content)

    with pdfplumber.open("/tmp/materia.pdf") as pdf:
        texto = ""
        for page in pdf.pages:
            texto += page.extract_text().replace("\n", " ")

    texto = re.sub(r'\s+', ' ', texto).strip()
    texto = re.sub(r'-\s+(\d+)', r'-\1', texto)  # Corrige matrículas quebradas

    # Quebra o texto em blocos por portaria
    blocos = re.split(r'(PORTARIA\s+Nº\s+\d+\s*-\s*\d{2}/\d{2}/\d{4}\.)', texto)

    registros = []

    for i in range(1, len(blocos), 2):
        cabecalho = blocos[i]
        corpo = blocos[i+1]
        bloco_texto = (cabecalho + " " + corpo).strip()

        if "calculados sobre a média das contribuições" not in bloco_texto.lower():
            continue

        # Número da portaria e data
        try:
            portaria_match = re.search(r'PORTARIA\s+Nº\s+(\d+)\s*-\s*(\d{2}/\d{2}/\d{4})', cabecalho, flags=re.IGNORECASE)
            numero_portaria = portaria_match.group(1)
            data_portaria = portaria_match.group(2)
        except:
            numero_portaria = ""
            data_portaria = ""

        # Nome
        try:
            idx_matricula = bloco_texto.lower().find(", matrícula")
            texto_ate_matricula = bloco_texto[:idx_matricula]
            idx_a = max(
                texto_ate_matricula.rfind(" à "),
                texto_ate_matricula.rfind(" a "),
                texto_ate_matricula.rfind(" de ")
            )
            nome = texto_ate_matricula[idx_a+3:].strip() if idx_a != -1 else ""
        except:
            nome = ""

        # Matrícula (valida formato com 12 caracteres)
        try:
            match_matricula = re.search(
                r'(\d{7}-\d-\d{2})', bloco_texto
            )
            matricula = match_matricula.group(1).strip() if match_matricula else ""
        except:
            matricula = ""

        # Cargo
        try:
            cargo = bloco_texto.split("no cargo de")[-1].split(",")[0].strip()
        except:
            cargo = ""

        # Órgão — última palavra entre '-' e '.'
        try:
            orgao_match = re.search(r'-\s*([A-Z]+)\.', bloco_texto)
            orgao = orgao_match.group(1).strip() if orgao_match else ""
        except:
            orgao = ""

        registros.append((nome, matricula, cargo, orgao, numero_portaria, data_portaria))

    return registros

# === Etapa 4: Processa todas as matérias e coleta todos os registros válidos ===
resultados = []
for item in tqdm(dados, desc="📄 Processando matérias"):
    url_pdf = obter_pdf_url(item["cdJornal"], item["cd_materia"])
    if not url_pdf:
        continue

    registros_pdf = extrair_detalhes_pdf(url_pdf)

    for nome, matricula, cargo, orgao, numero_portaria, data_portaria in registros_pdf:
        resultados.append({
            "Nome do Servidor": nome,
            "Matrícula": matricula,
            "Cargo": cargo,
            "Órgão de Origem": orgao,
            "Data de Publicação do DOE": item["dtPublicacaoJornal"][:10],
            "Número da Edição do DOE": item["vlNumero"],
            "Número da Portaria": numero_portaria,
            "Data da Portaria": data_portaria
        })

# Converte para DataFrame
df_final = pd.DataFrame(resultados)

# === Etapa 5: Salva Excel ===
df_final.to_excel("portarias_doe.xlsx", index=False)
print("📁 Arquivo Excel gerado: portarias_doe.xlsx")

from google.colab import files
files.download("portarias_doe.xlsx")
files.download("portarias_doe.xlsx")
