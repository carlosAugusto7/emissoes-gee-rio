"""
ETL das emissões de GEE da cidade do Rio de Janeiro (Tabela 3696, Data.Rio/IPP).

Fluxo determinístico:
    data/raw/3696.xls  ->  data/processed/emissoes_long.csv.gz
                           data/processed/emissoes_setores.csv.gz
                           data/processed/etl_log.txt

Uso:
    python -m src.etl                      # caminhos padrão
    python -m src.etl --raw caminho.xls    # arquivo bruto alternativo

Cada decisão de limpeza é registrada em LOG e gravada em
data/processed/etl_log.txt (rastreabilidade: nada em data/raw é alterado).
Se qualquer validação falhar, o script lança erro (código de saída 1) e NÃO grava dados processados.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DEFAULT = ROOT / "data" / "raw" / "3696.xls"
OUT_DIR = ROOT / "data" / "processed"

# Abas da planilha e rótulos das colunas de cada visão.
ABAS = {
    "3696_Escopos": ("escopo", ["Escopo 1", "Escopo 2", "Escopo 3", "Total"]),
    "3696_GEE": ("gas", ["CO2", "CH4", "N2O", "Total"]),
}

# Setores de primeiro nível (metodologia GPC).
SETORES = [
    "Energia Estacionária",
    "Transportes",
    "Resíduos",
    "Processos Industriais e Uso de Produtos",
    "Agropecuária, Floresta e Uso do Solo",
]

LOG: list[str] = []


def _norm(txt: object) -> str:
    """Remove espaços extras e notas de rodapé '(1)'/'(2)'; corrige grafias da fonte."""
    s = re.sub(r"\s+", " ", str(txt)).strip()
    s = re.sub(r"\s*\(\d\)$", "", s)
    fixes = {
        "Ferrroviário": "Ferroviário",
        "Incineração e Queima à Ceu Aberto": "Incineração e Queima à Céu Aberto",
    }
    return fixes.get(s, s)


def _to_num(v: object) -> float:
    """'-' = zero (nota 5); '(0)' = zero por arredondamento; '...' = não aplicável/indisponível;
    'NE' = não estimado (aparece em Compostagem/Escopo 3). Os dois últimos viram NaN."""
    if isinstance(v, (int, float, np.number)):
        return float(v)
    s = str(v).strip()
    if s in {"-", "(0)", "0"}:
        return 0.0
    if s in {"...", "NE", "", "nan"}:
        return np.nan
    return float(s.replace(".", "").replace(",", "."))


def read_raw(path: Path, sheet: str) -> pd.DataFrame:
    """Lê uma aba bruta sem cabeçalho (.xls exige xlrd; .xlsx usa openpyxl)."""
    return pd.read_excel(path, sheet_name=sheet, header=None)


def parse_sheet(raw: pd.DataFrame, dimensao: str) -> pd.DataFrame:
    """Converte a tabela larga (anos x componentes nas colunas) para formato longo."""
    # Linha 3: anos (preenchidos só na 1ª coluna de cada bloco). Linha 4: componentes.
    anos = raw.iloc[3, 1:].ffill().astype(int).tolist()
    comps = raw.iloc[4, 1:].astype(str).str.strip().tolist()
    rotulos = raw.iloc[:, 0].tolist()
    idx_total = next(i for i, r in enumerate(rotulos) if str(r).strip() == "TOTAL")
    idx_fim = next(i for i, r in enumerate(rotulos) if str(r).strip().startswith("Fonte"))

    registros = []
    setor_atual = None
    for i in range(6, idx_fim):
        rot = rotulos[i]
        if pd.isna(rot) or not str(rot).strip():
            continue
        nome = _norm(rot)
        if nome in SETORES:
            nivel, setor_atual, soma = "setor", nome, True
            setor = nome
        elif nome == "TOTAL":
            nivel, soma, setor = "total", True, "TOTAL"
        elif i > idx_total:  # itens informativos: não somam no total (GPC)
            nivel, soma, setor = "memo", False, "Memo (fora do total)"
            if nome.startswith("Compostagem"):
                nome = "Compostagem (memo)"
        else:
            nivel, soma, setor = "subsetor", True, setor_atual
        for j, (ano, comp) in enumerate(zip(anos, comps), start=1):
            registros.append(
                {
                    "dimensao": dimensao,
                    "ano": ano,
                    "componente": comp,
                    "nivel": nivel,
                    "setor": setor,
                    "categoria": nome,
                    "soma_no_total": soma,
                    "valor_tco2e": _to_num(raw.iat[i, j]),
                }
            )
    return pd.DataFrame(registros)


TOL = 1e-3  # tolerância (t CO2e) para as checagens de soma; os dados são publicados com arredondamento muito menor
ANOS_ESPERADOS = list(range(2012, 2025))


def validar(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Checagens de consistência. Devolve (mensagens para o log, erros que devem interromper o ETL)."""
    msgs: list[str] = []
    erros: list[str] = []

    # 1) estrutura esperada
    anos = sorted(int(a) for a in df["ano"].unique())
    if anos != ANOS_ESPERADOS:
        erros.append(f"Anos encontrados {anos[0]}-{anos[-1]} ({len(anos)}); esperado 2012-2024 (13 anos)")
    setores = set(df.loc[df.nivel == "setor", "categoria"])
    if setores != set(SETORES):
        erros.append(f"Setores encontrados diferem do esperado: faltam {sorted(set(SETORES) - setores)}, sobram {sorted(setores - set(SETORES))}")
    if df["nivel"].eq("total").sum() == 0:
        erros.append("Linha TOTAL não encontrada")
    msgs.append(f"Estrutura: {len(anos)} anos, {len(setores)} setores")

    # 2) TOTAL e setores não podem ter valor ausente
    chave = df[(df.componente == "Total") & df.nivel.isin(["setor", "total"])]
    n_nan = int(chave["valor_tco2e"].isna().sum())
    if n_nan:
        erros.append(f"{n_nan} valores ausentes em setores/TOTAL (componente Total)")

    # 3) os 5 setores somam o TOTAL publicado
    tot = df[(df.nivel == "total") & (df.componente == "Total")].set_index(["dimensao", "ano"])["valor_tco2e"]
    soma = (
        df[(df.nivel == "setor") & (df.componente == "Total")]
        .groupby(["dimensao", "ano"], observed=True)["valor_tco2e"]
        .sum()
    )
    dif = (tot - soma).abs().max()
    msgs.append(f"Soma dos 5 setores vs TOTAL: diferença máxima = {dif:,.4f} tCO2e")
    if not dif <= TOL:
        erros.append(f"Soma dos setores difere do TOTAL em até {dif:,.4f} tCO2e (tolerância {TOL})")

    # 4) as partes (escopos ou gases) somam o Total de cada setor/ano
    for dim, partes in [("escopo", ["Escopo 1", "Escopo 2", "Escopo 3"]), ("gas", ["CO2", "CH4", "N2O"])]:
        d = df[(df.dimensao == dim) & (df.nivel == "setor")]
        p = d.pivot_table(index=["ano", "categoria"], columns="componente", values="valor_tco2e", observed=True)
        err = (p[partes].sum(axis=1) - p["Total"]).abs().max()
        msgs.append(f"{dim}: máx |soma das partes - Total| por setor/ano = {err:,.4f} tCO2e")
        if not err <= TOL:
            erros.append(f"{dim}: soma das partes difere do Total em até {err:,.4f} tCO2e (tolerância {TOL})")

    # 5) as duas abas devem trazer o mesmo TOTAL
    t = df[(df.nivel == "total") & (df.componente == "Total")].pivot_table(index="ano", columns="dimensao", values="valor_tco2e")
    dif_abas = (t["escopo"] - t["gas"]).abs().max()
    msgs.append(f"TOTAL aba Escopos vs aba GEE: diferença máxima = {dif_abas:,.4f} tCO2e")
    if not dif_abas <= TOL:
        erros.append(f"TOTAL difere entre as abas em até {dif_abas:,.4f} tCO2e")
    return msgs, erros


def run(raw_path: Path = RAW_DEFAULT, out_dir: Path = OUT_DIR) -> pd.DataFrame:
    LOG.clear()
    out_dir.mkdir(parents=True, exist_ok=True)
    partes = []
    for aba, (dim, _) in ABAS.items():
        bruto = read_raw(raw_path, aba)
        LOG.append(f"[{aba}] aba lida com formato {bruto.shape} (linhas x colunas)")
        partes.append(parse_sheet(bruto, dim))
    df = pd.concat(partes, ignore_index=True)

    LOG.append(f"Valores ausentes ('...' e 'NE') mantidos como NaN, sem imputação: {int(df['valor_tco2e'].isna().sum())}")
    LOG.append(f"Células '-' ou '(0)' convertidas para 0.0: {int((df['valor_tco2e'] == 0).sum())}")
    LOG.append("Grafias corrigidas: 'Ferrroviário'->'Ferroviário'; 'Ceu'->'Céu'")
    msgs, erros = validar(df)
    LOG.extend(msgs)
    if erros:
        # grava o log para diagnóstico, mas NÃO grava nenhum dado processado
        LOG.extend(f"ERRO DE VALIDAÇÃO: {e}" for e in erros)
        (out_dir / "etl_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
        raise ValueError("Validação falhou; nenhum arquivo processado foi gravado:\n  - " + "\n  - ".join(erros))
    LOG.append("Validação: todas as checagens passaram")

    df["ano"] = df["ano"].astype("int16")
    df.to_csv(out_dir / "emissoes_long.csv.gz", index=False, compression="gzip")

    # Visão enxuta: 5 setores + TOTAL, componente 'Total' (idêntico nas duas abas).
    setores = (
        df[(df.dimensao == "escopo") & (df.componente == "Total") & df.nivel.isin(["setor", "total"])]
        .pivot_table(index="ano", columns="categoria", values="valor_tco2e", observed=True)
    )
    setores.to_csv(out_dir / "emissoes_setores.csv.gz", compression="gzip")
    (out_dir / "etl_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, default=RAW_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    try:
        run(args.raw, args.out)
    except ValueError as e:
        raise SystemExit(f"ERRO: {e}")  # código de saída 1: interrompe scripts e pipelines
    print("\n".join(LOG))
