# Dicionário de dados

Fonte: Instituto Municipal de Urbanismo Pereira Passos (IPP) / Data.Rio — Tabela 3696,
*Emissões de gases de efeito estufa (GEE) da Cidade do Rio de Janeiro, em t CO2e, 2012 a 2024* (set/2026).
<https://www.data.rio/documents/d242a8866bb64769a00958e925f43350/about>

Metodologia: GPC (Global Protocol for Community-Scale GHG Emission Inventories). Valores já em CO2e com GWP do AR5/IPCC.

## `data/raw/3696.xls` (bruto, não alterado)
| Aba | Conteúdo |
|---|---|
| `3696_Escopos` | Emissões por setor/subsetor × ano × (Escopo 1, Escopo 2, Escopo 3, Total) |
| `3696_GEE` | Emissões por setor/subsetor × ano × (CO2, CH4, N2O, Total) |
| `ESRI_MAPINFO_SHEET` | Aba técnica vazia (ignorada) |

Símbolos da fonte: `-` zero não resultante de arredondamento; `(0)` zero por arredondamento; `...` não aplicável/indisponível; `NE` não estimado.

## `data/processed/emissoes_long.csv.gz` (formato longo, 4.056 linhas)
| Variável | Tipo | Formato / domínio | Significado |
|---|---|---|---|
| `dimensao` | texto | `escopo` \| `gas` | Aba de origem: a coluna `componente` é um escopo ou um gás |
| `ano` | inteiro | 2012–2024 | Ano do inventário |
| `componente` | texto | `Escopo 1/2/3`, `CO2`, `CH4`, `N2O`, `Total` | Recorte da emissão (escopo GPC ou gás) |
| `nivel` | texto | `setor` \| `subsetor` \| `total` \| `memo` | Nível hierárquico da linha |
| `setor` | texto | 5 setores GPC, `TOTAL` ou `Memo (fora do total)` | Setor a que a categoria pertence |
| `categoria` | texto | ex.: `Rodoviário`, `Aterramento` | Nome da linha original, normalizado |
| `soma_no_total` | booleano | `True`/`False` | `False` para itens *memo*, que não entram no total (regra GPC) |
| `valor_tco2e` | decimal | t CO2e; pode ser negativo ou vazio | Emissão (positiva) ou remoção (negativa) em toneladas de CO2 equivalente |

Observações: valores negativos = remoções (reflorestamento, arborização urbana). Valores vazios (`NaN`) = `...` ou `NE`; não foram imputados.
Os componentes `Escopo 1/2/3` somam `Total`; `CO2/CH4/N2O` somam `Total`. Os 5 setores somam o `TOTAL`.

## `data/processed/emissoes_setores.csv.gz` (visão larga)
Linhas: `ano`. Colunas: os 5 setores e `TOTAL` (t CO2e).

## `data/processed/etl_log.txt`
Registro das decisões e validações da última execução de `src/etl.py`.

## Setores GPC
Energia Estacionária · Transportes · Resíduos · Processos Industriais e Uso de Produtos · Agropecuária, Floresta e Uso do Solo.
