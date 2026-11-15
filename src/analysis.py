"""
Análise exploratória: métricas agregadas e figuras estáticas do artigo.

Entrada : data/processed/emissoes_long.csv.gz  (gerado por src/etl.py)
Saídas  : docs/assets/*.png  e  docs/assets/metrics.json

Uso:
    python -m src.analysis
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed" / "emissoes_long.csv.gz"
ASSETS = ROOT / "docs" / "assets"

SETORES = [
    "Energia Estacionária",
    "Transportes",
    "Resíduos",
    "Processos Industriais e Uso de Produtos",
    "Agropecuária, Floresta e Uso do Solo",
]
# Paleta segura para daltonismo (Okabe-Ito)
COR_SETOR = {
    "Energia Estacionária": "#0072B2",
    "Transportes": "#E69F00",
    "Resíduos": "#009E73",
    "Processos Industriais e Uso de Produtos": "#CC79A7",
    "Agropecuária, Floresta e Uso do Solo": "#999999",
}
COR_ESCOPO = {"Escopo 1": "#0072B2", "Escopo 2": "#D55E00", "Escopo 3": "#56B4E9"}
COR_GAS = {"CO2": "#444444", "CH4": "#E69F00", "N2O": "#CC79A7"}
MT = 1e6  # toneladas -> milhões de toneladas

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "figure.dpi": 100,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
    }
)


# --------------------------------------------------------------------------- dados
def carregar(path: Path = PROC) -> pd.DataFrame:
    return pd.read_csv(path)


def tabela_setores(df: pd.DataFrame) -> pd.DataFrame:
    d = df[(df.dimensao == "escopo") & (df.componente == "Total") & (df.nivel == "setor")]
    return d.pivot_table(index="ano", columns="categoria", values="valor_tco2e")[SETORES]


def tabela_total(df: pd.DataFrame, dim: str) -> pd.DataFrame:
    d = df[(df.dimensao == dim) & (df.nivel == "total")]
    return d.pivot_table(index="ano", columns="componente", values="valor_tco2e")


def tabela_subsetores(df: pd.DataFrame) -> pd.DataFrame:
    d = df[(df.dimensao == "escopo") & (df.componente == "Total") & (df.nivel == "subsetor")]
    return d.pivot_table(index="categoria", columns="ano", values="valor_tco2e")


def serie_sin(df: pd.DataFrame) -> pd.Series:
    d = df[(df.nivel == "memo") & (df.dimensao == "escopo") & (df.componente == "Total")]
    d = d[d.categoria.str.contains("Sistema Interligado")]
    return d.set_index("ano")["valor_tco2e"]


# --------------------------------------------------------------------------- métricas
def pct(a: float, b: float) -> float:
    return (b / a - 1) * 100


def calcular_metricas(df: pd.DataFrame) -> dict:
    s = tabela_setores(df)
    tot = s.sum(axis=1)
    esc = tabela_total(df, "escopo")
    gas = tabela_total(df, "gas")
    sub = tabela_subsetores(df)
    sin = serie_sin(df)
    anos = tot.index.values

    lin = stats.linregress(anos, tot.values)
    part = s.div(tot, axis=0) * 100
    delta = (sub[2024] - sub[2012]).sort_values()
    cv = lambda x: float(x.std() / x.mean() * 100)  # noqa: E731

    m = {
        "total": {int(a): float(v) for a, v in tot.items()},
        "total_2012": float(tot[2012]),
        "total_2024": float(tot[2024]),
        "var_2012_2024_pct": pct(tot[2012], tot[2024]),
        "pico_ano": int(tot.idxmax()),
        "pico_valor": float(tot.max()),
        "min_ano": int(tot.idxmin()),
        "min_valor": float(tot.min()),
        "var_2014_2024_pct": pct(tot[2014], tot[2024]),
        "var_2019_2020_pct": pct(tot[2019], tot[2020]),
        "var_2020_2021_pct": pct(tot[2020], tot[2021]),
        "cagr_total_pct": float(((tot[2024] / tot[2012]) ** (1 / 12) - 1) * 100),
        "tendencia_t_por_ano": float(lin.slope),
        "tendencia_r2": float(lin.rvalue**2),
        "tendencia_p": float(lin.pvalue),
        "participacao_pct": {str(a): {k: float(v) for k, v in part.loc[a].items()} for a in (2012, 2019, 2024)},
        "var_setor_2012_2024_pct": {k: pct(s[k][2012], s[k][2024]) for k in SETORES},
        "cv_setor_pct": {k: cv(s[k]) for k in SETORES},
        "cv_total_pct": cv(tot),
        "escopo_participacao_pct": {
            str(a): {k: float(esc.loc[a, k] / esc.loc[a, "Total"] * 100) for k in COR_ESCOPO} for a in (2012, 2014, 2021, 2022, 2024)
        },
        "cv_escopo_pct": {k: cv(esc[k]) for k in COR_ESCOPO},
        "escopo2_max": [int(esc["Escopo 2"].idxmax()), float(esc["Escopo 2"].max())],
        "escopo2_min": [int(esc["Escopo 2"].idxmin()), float(esc["Escopo 2"].min())],
        "corr_escopo2_sin": float(np.corrcoef(esc["Escopo 2"], sin)[0, 1]),
        "gas_participacao_pct": {
            str(a): {k: float(gas.loc[a, k] / gas.loc[a, "Total"] * 100) for k in COR_GAS} for a in (2012, 2018, 2024)
        },
        "var_gas_2012_2024_pct": {k: pct(gas[k][2012], gas[k][2024]) for k in COR_GAS},
        "delta_subsetor_2012_2024": {k: float(v) for k, v in delta.items()},
        "soma_deltas_top3_queda": float(delta.iloc[:3].sum()),
        "delta_total": float(tot[2024] - tot[2012]),
    }
    return m


# --------------------------------------------------------------------------- figuras
def fig_total_setores(df: pd.DataFrame, out: Path) -> None:
    s = tabela_setores(df) / MT
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.stackplot(s.index, [s[c] for c in SETORES], labels=SETORES, colors=[COR_SETOR[c] for c in SETORES], alpha=0.92)
    tot = s.sum(axis=1)
    ax.plot(tot.index, tot.values, color="black", lw=1.5)
    for ano, txt, ytxt in [(2014, "pico", 25.6), (2020, "mínimo", 24.0)]:
        ax.annotate(f"{txt}: {tot[ano]:.1f} Mt ({ano})", (ano, tot[ano]), (ano, ytxt), ha="center", fontsize=9,
                    arrowprops=dict(arrowstyle="-", lw=0.6))
    ax.set_ylabel("Milhões de t CO₂e")
    ax.set_xlabel("Ano")
    ax.set_xticks(s.index)
    ax.set_xlim(2012, 2024)
    ax.set_ylim(0, 27)
    ax.set_title("Emissões de GEE do Rio de Janeiro por setor, 2012–2024")
    ax.legend(loc="lower left", fontsize=8, frameon=True, ncol=2)
    fig.text(0.01, -0.02, "Fonte: Data.Rio/IPP, Tabela 3696. Elaboração própria.", fontsize=8, color="#555")
    fig.savefig(out / "fig1_total_setores.png")
    plt.close(fig)


def fig_participacao(df: pd.DataFrame, out: Path) -> None:
    s = tabela_setores(df)
    part = s.div(s.sum(axis=1), axis=0) * 100
    anos = [2012, 2019, 2024]
    cores = ["#B8D4EA", "#5A9BD5", "#1F4E79"]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    y = np.arange(len(SETORES))
    h = 0.26
    for i, (a, c) in enumerate(zip(anos, cores)):
        v = [part.loc[a, k] for k in SETORES]
        bars = ax.barh(y + (1 - i) * h, v, h, label=str(a), color=c)
        for b, val in zip(bars, v):
            ax.text(val + 0.5, b.get_y() + b.get_height() / 2, f"{val:.1f}%", va="center", fontsize=8)
    ax.set_yticks(y)
    ax.set_yticklabels([k.replace(" e Uso do Solo", "\ne Uso do Solo").replace("Processos Industriais e", "Processos Industriais\ne") for k in SETORES], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Participação no total do inventário (%)")
    ax.set_xlim(0, 55)
    ax.set_title("Composição setorial das emissões: 2012, 2019 e 2024")
    ax.legend(title="Ano", loc="lower right")
    fig.savefig(out / "fig2_participacao.png")
    plt.close(fig)


def fig_escopos(df: pd.DataFrame, out: Path) -> None:
    esc = tabela_total(df, "escopo")[list(COR_ESCOPO)] / MT
    sin = serie_sin(df) / MT
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1.5, 1]})
    ax = axes[0]
    bottom = np.zeros(len(esc))
    for k in COR_ESCOPO:
        ax.bar(esc.index, esc[k], bottom=bottom, label=k, color=COR_ESCOPO[k])
        bottom += esc[k].values
    ax.set_xticks(esc.index)
    ax.set_xticklabels(esc.index, rotation=45, fontsize=8)
    ax.set_ylabel("Milhões de t CO₂e")
    ax.set_title("Emissões por escopo (GPC)")
    ax.legend(fontsize=8)
    ax = axes[1]
    ax.scatter(sin, esc["Escopo 2"], color=COR_ESCOPO["Escopo 2"], s=36, zorder=3)
    for a in esc.index:
        ax.annotate(str(a)[2:], (sin[a], esc["Escopo 2"][a]), textcoords="offset points", xytext=(4, 3), fontsize=7)
    r = np.corrcoef(sin, esc["Escopo 2"])[0, 1]
    b1, b0 = np.polyfit(sin, esc["Escopo 2"], 1)
    xs = np.linspace(sin.min(), sin.max(), 20)
    ax.plot(xs, b0 + b1 * xs, "--", color="#555", lw=1)
    ax.set_xlabel("Geração p/ o SIN no território (Mt CO₂e)")
    ax.set_ylabel("Escopo 2 (Mt CO₂e)")
    ax.set_title(f"Escopo 2 × geração para o SIN (r = {r:.2f})")
    fig.tight_layout()
    fig.savefig(out / "fig3_escopos.png")
    plt.close(fig)


def fig_gases(df: pd.DataFrame, out: Path) -> None:
    g = tabela_total(df, "gas")[list(COR_GAS)]
    share = g.div(g.sum(axis=1), axis=0) * 100
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax = axes[0]
    ax.stackplot(g.index, [g[k] / MT for k in COR_GAS], labels=list(COR_GAS), colors=list(COR_GAS.values()))
    ax.set_ylabel("Milhões de t CO₂e")
    ax.set_xticks(g.index[::2])
    ax.set_title("Emissões por gás (t CO₂e)")
    ax.legend(loc="lower left", fontsize=8)
    ax = axes[1]
    for k in ["CH4", "N2O"]:
        ax.plot(share.index, share[k], marker="o", color=COR_GAS[k], label=k)
    ax.set_ylabel("Participação no total (%)")
    ax.set_xticks(g.index[::2])
    ax.set_title("Participação de CH₄ e N₂O")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig4_gases.png")
    plt.close(fig)


def fig_variacao_subsetores(df: pd.DataFrame, out: Path, n: int = 7) -> None:
    sub = tabela_subsetores(df)
    delta = ((sub[2024] - sub[2012]) / MT).sort_values()
    sel = pd.concat([delta.head(n), delta.tail(n)])
    cores = ["#009E73" if v < 0 else "#D55E00" for v in sel]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.barh(sel.index, sel.values, color=cores)
    for i, v in enumerate(sel.values):
        ax.text(v + (0.03 if v >= 0 else -0.03), i, f"{v:+.2f}", va="center", ha="left" if v >= 0 else "right", fontsize=8)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Variação 2012→2024 (milhões de t CO₂e)")
    ax.set_title(f"Subsetores com maiores reduções e aumentos absolutos")
    ax.set_xlim(-1.6, 0.8)
    ax.tick_params(axis="y", labelsize=8)
    fig.savefig(out / "fig5_variacao_subsetores.png")
    plt.close(fig)


def main() -> dict:
    ASSETS.mkdir(parents=True, exist_ok=True)
    df = carregar()
    fig_total_setores(df, ASSETS)
    fig_participacao(df, ASSETS)
    fig_escopos(df, ASSETS)
    fig_gases(df, ASSETS)
    fig_variacao_subsetores(df, ASSETS)
    m = calcular_metricas(df)
    (ASSETS / "metrics.json").write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    return m


if __name__ == "__main__":
    m = main()
    print(f"Figuras e métricas gravadas em {ASSETS}")
    print(f"Variação 2012→2024: {m['var_2012_2024_pct']:.1f}% | pico {m['pico_ano']} | mínimo {m['min_ano']}")
