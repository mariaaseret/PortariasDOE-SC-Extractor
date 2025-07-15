
# 📄 Coletor de Portarias do DOE/SC

Este script coleta automaticamente portarias publicadas no Diário Oficial do Estado de Santa Catarina, que contenham a expressão **“calculados sobre a média das contribuições”**, e gera uma planilha Excel com os dados principais.

---

## 🚀 Como funciona

O script percorre as edições do DOE no período configurado e executa as seguintes etapas:

### 1️⃣ Consulta inicial à API

Primeiro o script busca todas as matérias publicadas para um dado ano e mês, com o termo desejado:

```
https://portal.doe.sea.sc.gov.br/apis/materia/materia?ano=2025&mes=7&dataInicio=&dataFim=&assunto=35&categoria=4704302&dsMateria=calculados%20sobre%20a%20m%C3%A9dia%20das%20contribui%C3%A7%C3%B5es&tipoBusca=1&sortEdicao=&numeroEdicao=&numeroMateria=&ondePesquisar=4
```

Essa API retorna uma lista de matérias com identificadores (`cdJornal` e `cd_materia`).

---

### 2️⃣ Busca do PDF da matéria

Para cada matéria retornada, o script consulta uma segunda API para obter o link direto para o PDF da matéria específica:

```
https://portal.doe.sea.sc.gov.br/apis/edicao-preview/extrato/edicao/{cdJornal}/materia/{cd_materia}
```

Exemplo:
```
https://portal.doe.sea.sc.gov.br/apis/edicao-preview/extrato/edicao/4099/materia/1094369
```

Essa chamada devolve um JSON com a URL do PDF:
```
"urlExtratoArquivo": "https://portal.doe.sea.sc.gov.br/repositorio/2025/20250707/Materias/1094369/extrato_materia-1094369.pdf"
```

---

### 3️⃣ Extração dos dados

O PDF é baixado e processado com `pdfplumber` para extrair os seguintes dados:
- Nome do servidor
- Matrícula
- Cargo
- Órgão de origem
- Data de publicação do DOE
- Número da edição do DOE
- Número da portaria
- Data da portaria

O script trata quebras de linha e espaços extras para capturar corretamente o nome completo do servidor.

---

### 4️⃣ Geração da planilha

Todos os registros são salvos em um arquivo:
✅ `portarias_doe.xlsx`

A planilha é automaticamente baixada no final da execução.

---

## 🧰 Requisitos

- Python 3.8+
- Google Colab (ou ambiente local com bibliotecas instaladas)

### Bibliotecas usadas:
- `requests`
- `pandas`
- `pdfplumber`
- `tqdm`
- `re` (inclusa na biblioteca padrão)

---

## 📝 Como rodar

📌 No Google Colab:
1. Cole o script no notebook.
2. Execute as células.
3. Baixe o arquivo gerado (`portarias_doe.xlsx`).

---

## ✍️ Créditos

Desenvolvido por MARIA TERESA SILVA SANTOS com apoio do Auditor  ADEMAR SENABIO FILHO.
