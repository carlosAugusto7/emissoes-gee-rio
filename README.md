# Emissões de GEE da cidade do Rio de Janeiro (2012–2024)

![Python](https://img.shields.io/badge/python-3.12-blue) ![Licença código](https://img.shields.io/badge/código-MIT-green) ![Licença dados](https://img.shields.io/badge/dados%20e%20texto-CC%20BY%204.0-lightgrey) ![FAIR](https://img.shields.io/badge/FAIR-compliant-success)

Projeto final da disciplina Linguagem de Programação 
Bacharelado em Sistemas de Informação
6º período · Centro Universitário La Salle · Semestre 2026/2
Professor: Alexandre Neves Louzada
Autores: Carlos Augusto Ferreira Souza; Wilson da Silva Prata Junior

📄 **Artigo (GitHub Pages):** https://carlosAugusto7.github.io/emissoes-gee-rio/

## Resumo executivo
Pipeline determinístico em Python que converte a Tabela 3696 do Data.Rio/IPP (emissões de gases de efeito estufa da cidade do Rio de Janeiro, metodologia GPC, 2012–2024) em um conjunto de dados longo, validado e aberto, e o explora por setor, escopo e gás.

Principais achados:
- Emissões totais: **22,27 Mt CO₂e (2012) → 19,84 Mt (2024), −10,9%**; pico em 2014 (24,17 Mt) e mínimo em 2020 (17,36 Mt).
- Energia estacionária (45,5%) e transportes (33,1%) concentram ~79% do total em 2024.
- O **Escopo 2** é o mais volátil (CV ≈ 40%) e se associa à geração para o sistema elétrico nacional (r ≈ 0,67).
- A redução líquida vem de aviação, transporte rodoviário e siderurgia; o metano sobe de 9,3% para 11,9% das emissões, ligado ao aterramento de resíduos.

**Perguntas de pesquisa:** RQ1 evolução do total e da composição setorial · RQ2 volatilidade por escopo · RQ3 subsetores e gases por trás da variação líquida.

**Palavras-chave:** emissões de gases de efeito estufa; inventário GPC; Rio de Janeiro; análise exploratória de dados; FAIR.

## Fonte dos dados
Instituto Municipal de Urbanismo Pereira Passos (IPP) / Data.Rio — Tabela 3696, set/2026:
<https://www.data.rio/documents/d242a8866bb64769a00958e925f43350/about>

## Estrutura
```
├── README.md · LICENSE · requirements.txt · .gitignore
├── data/
│   ├── raw/3696.xls                 # bruto, intocado
│   ├── processed/                   # emissoes_long.csv.gz, emissoes_setores.csv.gz, etl_log.txt
│   └── data_dictionary.md           # dicionário de variáveis (FAIR)
├── notebooks/analise_exploratoria.ipynb
├── src/                             # etl.py (limpeza) · analysis.py (métricas/figuras) · build_site.py (artigo)
└── docs/                            # artigo publicado: index.html + assets/
```

## Como reproduzir
1. **Clone o repositório e entre na pasta:**
```bash
git clone [https://github.com/carlosAugusto7/emissoes-gee-rio.git](https://github.com/carlosAugusto7/emissoes-gee-rio.git)
cd emissoes-gee-rio
```

2. **Crie e ative o ambiente virtual (`.venv`):**

* **Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

* **Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. **Instale as dependências e execute o pipeline:**
```bash
pip install -r requirements.txt
python -m src.etl            # data/raw -> data/processed
python -m src.analysis       # figuras e métricas -> docs/assets
python -m src.build_site     # gera docs/index.html
jupyter lab
```

## Publicação no GitHub Pages
Settings → Pages → *Deploy from a branch* → branch `main`, pasta `/docs`.

## Licenças
Código: MIT. Texto e dados processados: CC BY 4.0. Dados brutos: IPP/Data.Rio.
