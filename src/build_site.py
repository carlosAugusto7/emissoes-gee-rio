from __future__ import annotations

import html
import json
import re
from pathlib import Path

from src import analysis

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "index.html"

# ------------------------------------------------------------------ CONFIG 
CONFIG = {
    "titulo": "Emissões de gases de efeito estufa da cidade do Rio de Janeiro (2012–2024): "
              "composição setorial, volatilidade por escopo e fatores da redução líquida",
    "autores": ["Carlos Augusto Ferreira Souza", "Wilson da Silva Prata Junior",],
    "curso": "Bacharelado em Sistemas de Informação — 6º período",
    "instituicao": "Centro Universitário La Salle",
    "disciplina": "Linguagem de Programação",
    "professor": "Prof. Alexandre Neves Louzada",
    "semestre": "2026/2",
    "repo_url": "https://github.com/carlosAugusto7/emissoes-gee-rio",
    "pages_url": "https://carlosAugusto7.github.io/emissoes-gee-rio/",
    "dados_url": "https://www.data.rio/documents/d242a8866bb64769a00958e925f43350/about",
}
# ------------------------------------------------------------------------------------

SNIPPETS = {
    "parse": '''def parse_sheet(raw: pd.DataFrame, dimensao: str) -> pd.DataFrame:
    """Converte a tabela larga (anos x componentes nas colunas) para formato longo."""
    anos = raw.iloc[3, 1:].ffill().astype(int).tolist()      # ano só aparece na 1ª coluna do bloco
    comps = raw.iloc[4, 1:].astype(str).str.strip().tolist()  # Escopo 1/2/3/Total ou CO2/CH4/N2O/Total
    ...
    for i in range(6, idx_fim):
        nome = _norm(rotulos[i])
        if nome in SETORES:            nivel = "setor"
        elif nome == "TOTAL":          nivel = "total"
        elif i > idx_total:            nivel = "memo"      # itens que NÃO somam no total (GPC)
        else:                          nivel = "subsetor"
        ...''',
    "num": '''def _to_num(v):
    """'-' = zero (nota 5); '(0)' = zero por arredondamento; '...' e 'NE' = ausente (NaN)."""
    if isinstance(v, (int, float, np.number)):
        return float(v)
    s = str(v).strip()
    if s in {"-", "(0)", "0"}:
        return 0.0
    if s in {"...", "NE", "", "nan"}:
        return np.nan''',
    "valid": '''tot = df[(df.nivel == "total") & (df.componente == "Total")].set_index(["dimensao", "ano"])["valor_tco2e"]
soma = (df[(df.nivel == "setor") & (df.componente == "Total")]
        .groupby(["dimensao", "ano"], observed=True)["valor_tco2e"].sum())
assert (tot - soma).abs().max() < 1e-3   # os 5 setores reproduzem exatamente o TOTAL publicado''',
}

CSS = """
:root{--bg:#fff;--fg:#1d2327;--mut:#5b6670;--line:#dfe4e8;--acc:#0b5cab;--card:#f6f8fa;--code:#0f1720;--codefg:#e6edf3}
@media (prefers-color-scheme:dark){:root{--bg:#12161a;--fg:#e6e9ec;--mut:#9aa6b0;--line:#2a3138;--acc:#6db3ff;--card:#1a2025}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.65 Georgia,'Times New Roman',serif}
.wrap{max-width:860px;margin:0 auto;padding:0 20px 80px}
header{padding:48px 0 24px;border-bottom:1px solid var(--line)}
header .kicker{font:600 13px/1 system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--acc)}
h1{font-size:clamp(1.55rem,4.2vw,2.15rem);line-height:1.25;margin:14px 0 18px}
.autores{font:16px/1.5 system-ui,sans-serif}.afil{font:14px/1.5 system-ui,sans-serif;color:var(--mut);margin-top:6px}
.badges{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px;font:600 12.5px/1 system-ui,sans-serif}
.badge{display:inline-block;padding:7px 10px;border-radius:6px;background:var(--card);border:1px solid var(--line);color:var(--fg);text-decoration:none}
.badge.gh{background:#24292f;color:#fff;border-color:#24292f}
h2{font-size:1.4rem;margin:44px 0 8px;padding-top:8px}h3{font-size:1.12rem;margin:28px 0 4px}
p{margin:.7em 0}a{color:var(--acc)}
.abstract{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 20px 14px;margin:28px 0}
.abstract h2{margin-top:14px;font-size:1.1rem}.kw{font:14px/1.5 system-ui,sans-serif;color:var(--mut)}
figure{margin:26px 0}figure img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px;background:#fff}
figcaption{font:14px/1.5 system-ui,sans-serif;color:var(--mut);margin-top:8px}
.plot{width:100%;min-height:380px}.ctrl{font:14px system-ui,sans-serif;margin:8px 0;display:flex;gap:14px;flex-wrap:wrap;align-items:center}
select{font:inherit;padding:4px 6px;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:4px}
pre{background:var(--code);color:var(--codefg);padding:14px 16px;border-radius:8px;overflow-x:auto;font:13px/1.55 ui-monospace,Menlo,Consolas,monospace}
code{font:.88em ui-monospace,Menlo,Consolas,monospace;background:var(--card);padding:1px 5px;border-radius:4px}pre code{background:none;padding:0}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font:14px/1.45 system-ui,sans-serif;margin:14px 0}
th,td{border-bottom:1px solid var(--line);padding:7px 10px;text-align:right}th:first-child,td:first-child{text-align:left}th{background:var(--card)}
.rq{border-left:4px solid var(--acc);padding:2px 14px;margin:12px 0;background:var(--card);border-radius:0 6px 6px 0}
.note{font:14px/1.5 system-ui,sans-serif;color:var(--mut)}
ol.refs{padding-left:1.3em;font-size:15.5px}ol.refs li{margin:.5em 0}
footer{margin-top:50px;padding-top:16px;border-top:1px solid var(--line);font:13px/1.5 system-ui,sans-serif;color:var(--mut)}
@media (max-width:560px){body{font-size:16px}h2{font-size:1.25rem}}
"""

JS = """
window.addEventListener('load', function(){
const D = __DATA__;
const cs = getComputedStyle(document.documentElement);
const FG = cs.getPropertyValue('--fg').trim() || '#1d2327';
const GRID = cs.getPropertyValue('--line').trim() || '#dfe4e8';
const base = (extra) => Object.assign({paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',
  font:{family:'system-ui,sans-serif',color:FG,size:13},margin:{l:62,r:14,t:30,b:50},
  xaxis:{gridcolor:GRID,dtick:1},yaxis:{gridcolor:GRID},legend:{orientation:'h',y:-0.22}}, extra||{});
const cfg = {responsive:true,displaylogo:false};
const fmt = (v)=> (v/1e6).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2});

/* Gráfico 1: setores empilhados (valor absoluto / participação) */
(function(){
  const traces = D.setores.map(s => ({type:'bar',name:s.nome,x:D.anos,y:s.valores.map(v=>v/1e6),marker:{color:s.cor},
    hovertemplate:'%{x}: %{y:.2f} Mt CO₂e<extra>'+s.nome+'</extra>'}));
  const lay = base({barmode:'stack',yaxis:{title:'Milhões de t CO₂e',gridcolor:GRID},
    updatemenus:[{type:'buttons',direction:'right',x:0,y:1.16,buttons:[
      {label:'Valores absolutos',method:'relayout',args:[{barnorm:'',  'yaxis.title':'Milhões de t CO₂e'}]},
      {label:'Participação (%)', method:'relayout',args:[{barnorm:'percent','yaxis.title':'% do total'}]}]}]});
  Plotly.newPlot('g1',traces,lay,cfg);
})();

/* Gráfico 2: escopos (linhas) */
(function(){
  const traces = D.escopos.map(s => ({type:'scatter',mode:'lines+markers',name:s.nome,x:D.anos,y:s.valores.map(v=>v/1e6),
    line:{color:s.cor,width:2.5},hovertemplate:'%{x}: %{y:.2f} Mt<extra>'+s.nome+'</extra>'}));
  Plotly.newPlot('g2',traces,base({yaxis:{title:'Milhões de t CO₂e',gridcolor:GRID,rangemode:'tozero'}}),cfg);
})();

/* Gráfico 3: explorador de variações por subsetor */
(function(){
  const a = document.getElementById('y0'), b = document.getElementById('y1');
  D.anos.forEach(y=>{a.add(new Option(y,y));b.add(new Option(y,y));});
  a.value = 2012; b.value = 2024;
  function draw(){
    const y0 = +a.value, y1 = +b.value, i0 = D.anos.indexOf(y0), i1 = D.anos.indexOf(y1);
    const rows = D.subsetores.map(s=>({n:s.nome,d:(s.valores[i1]-s.valores[i0])/1e6})).filter(r=>!isNaN(r.d));
    rows.sort((p,q)=>p.d-q.d);
    const sel = rows.slice(0,8).concat(rows.slice(-8)).filter((r,i,arr)=>arr.findIndex(x=>x.n===r.n)===i);
    const tr = [{type:'bar',orientation:'h',x:sel.map(r=>r.d),y:sel.map(r=>r.n),
      marker:{color:sel.map(r=>r.d<0?'#009E73':'#D55E00')},
      hovertemplate:'%{y}<br>%{x:+.3f} Mt CO₂e<extra></extra>'}];
    Plotly.react('g3',tr,base({margin:{l:250,r:14,t:20,b:50},xaxis:{title:'Variação '+y0+'→'+y1+' (milhões de t CO₂e)',gridcolor:GRID,zeroline:true},
      yaxis:{automargin:true,tickfont:{size:11}},height:520}),cfg);
  }
  a.onchange = b.onchange = draw; draw();
})();
});
"""


def fmt_mt(x: float) -> str:
    return f"{x / 1e6:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def montar_dados() -> dict:
    df = analysis.carregar()
    s = analysis.tabela_setores(df)
    esc = analysis.tabela_total(df, "escopo")
    sub = analysis.tabela_subsetores(df)
    anos = [int(a) for a in s.index]
    return {
        "anos": anos,
        "setores": [{"nome": k, "cor": analysis.COR_SETOR[k], "valores": [float(v) for v in s[k]]} for k in analysis.SETORES],
        "escopos": [{"nome": k, "cor": analysis.COR_ESCOPO[k], "valores": [float(v) for v in esc[k]]} for k in analysis.COR_ESCOPO],
        "subsetores": [
            {"nome": k, "valores": [None if v != v else float(v) for v in sub.loc[k, anos]]} for k in sub.index
        ],
    }


def tabela_resumo(m: dict) -> str:
    linhas = []
    for k in analysis.SETORES:
        p = m["participacao_pct"]
        linhas.append(
            f"<tr><td>{html.escape(k)}</td><td>{p['2012'][k]:.1f}%</td><td>{p['2019'][k]:.1f}%</td><td>{p['2024'][k]:.1f}%</td>"
            f"<td>{m['var_setor_2012_2024_pct'][k]:+.1f}%</td><td>{m['cv_setor_pct'][k]:.1f}%</td></tr>"
        )
    linhas.append(
        f"<tr><td><b>Total</b></td><td>100%</td><td>100%</td><td>100%</td>"
        f"<td><b>{m['var_2012_2024_pct']:+.1f}%</b></td><td>{m['cv_total_pct']:.1f}%</td></tr>"
    )
    return "\n".join(linhas)


def montar_html() -> str:
    c = CONFIG
    m = json.loads((analysis.ASSETS / "metrics.json").read_text(encoding="utf-8"))
    dados = montar_dados()
    esc = m["escopo_participacao_pct"]
    gas = m["gas_participacao_pct"]
    autores = ", ".join(html.escape(a) for a in c["autores"])
    code = {k: html.escape(v) for k, v in SNIPPETS.items()}

    resumo = (
        "As cidades precisam de inventários de gases de efeito estufa (GEE) para orientar metas de mitigação, mas séries "
        "publicadas em planilhas dificultam a análise reprodutível. Este trabalho constrói um pipeline determinístico em Python "
        "que converte a Tabela 3696 do Data.Rio/IPP, com as emissões da cidade do Rio de Janeiro entre 2012 e 2024 segundo a "
        "metodologia GPC, em um conjunto de dados longo, validado e aberto, e o explora por setor, escopo e gás. As emissões "
        f"totais passaram de {fmt_mt(m['total_2012'])} Mt CO₂e em 2012 para {fmt_mt(m['total_2024'])} Mt em 2024 "
        f"({m['var_2012_2024_pct']:.1f}%), com pico em {m['pico_ano']} e mínimo em {m['min_ano']}. Energia estacionária e transportes "
        f"concentram cerca de {m['participacao_pct']['2024']['Energia Estacionária'] + m['participacao_pct']['2024']['Transportes']:.0f}% do total. "
        f"O Escopo 2 (eletricidade) é o componente mais volátil (coeficiente de variação de {m['cv_escopo_pct']['Escopo 2']:.0f}%, contra "
        f"{m['cv_escopo_pct']['Escopo 1']:.0f}% do Escopo 1) e se associa moderadamente à geração para o sistema elétrico nacional. A "
        "redução líquida decorre sobretudo da aviação, do transporte rodoviário e da siderurgia, parcialmente compensada pelo aterramento "
        f"de resíduos; a participação do metano subiu de {gas['2012']['CH4']:.1f}% para {gas['2024']['CH4']:.1f}%. "
        "Discutem-se limitações da série e propostas de trabalhos futuros."
    )
    n_palavras = len(resumo.split())

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(c['titulo'])}</title>
<meta name="description" content="Análise reprodutível das emissões de GEE da cidade do Rio de Janeiro (2012–2024) a partir da Tabela 3696 do Data.Rio/IPP.">
<meta name="author" content="{autores}">
<meta name="keywords" content="emissões de gases de efeito estufa, inventário GPC, Rio de Janeiro, análise exploratória de dados, FAIR">
<link rel="license" href="https://creativecommons.org/licenses/by/4.0/">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" onerror="this.onerror=null;this.src='https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js'" defer></script>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="kicker">Projeto Final · {html.escape(c['disciplina'])}</div>
  <h1>{html.escape(c['titulo'])}</h1>
  <div class="autores"><b>{autores}</b></div>
  <div class="afil">{html.escape(c['curso'])} · {html.escape(c['instituicao'])}<br>
  {html.escape(c['professor'])} · Semestre {html.escape(c['semestre'])}</div>
  <div class="badges">
    <a class="badge gh" href="{c['repo_url']}">⌥ Repositório no GitHub</a>
    <span class="badge">Código: MIT</span><span class="badge">Dados e texto: CC BY 4.0</span>
    <span class="badge">FAIR</span><span class="badge">Python · pandas · Plotly</span>
    <a class="badge" href="{c['dados_url']}">Fonte: Data.Rio / IPP</a>
  </div>
</header>

<section class="abstract" id="resumo">
  <h2>Resumo</h2>
  <p>{resumo}</p>
  <p class="kw"><b>Palavras-chave:</b> emissões de gases de efeito estufa; inventário GPC; cidade do Rio de Janeiro; análise exploratória; ciência aberta (FAIR).</p>
</section>

<h2 id="intro">1. Introdução</h2>
<p>Cidades concentram grande parte das emissões antrópicas de gases de efeito estufa e, ao mesmo tempo, dispõem de instrumentos de política local (uso do solo, mobilidade, resíduos, edificações) para reduzi-las. O Global Protocol for Community-Scale Greenhouse Gas Emission Inventories (GPC) padronizou a contabilidade urbana de GEE em setores e em três escopos: emissões dentro do território (Escopo 1), emissões associadas à energia da rede consumida na cidade (Escopo 2) e emissões que ocorrem fora do território por atividades nele realizadas (Escopo 3) (WRI; C40; ICLEI, 2014).</p>
<p>O Instituto Municipal de Urbanismo Pereira Passos (IPP) publica no portal Data.Rio a série anual de emissões do Rio de Janeiro. A série traz detalhes valiosos, mas vem em planilha com cabeçalhos em dois níveis, itens informativos que não somam no total e símbolos de dado ausente, o que dificulta a reutilização direta. Este trabalho trata a tabela como um problema de engenharia de dados e, a partir dela, busca responder:</p>
<div class="rq"><b>RQ1.</b> Como evoluíram as emissões totais do Rio entre 2012 e 2024 e como mudou a composição setorial?</div>
<div class="rq"><b>RQ2.</b> Que componentes, por escopo, explicam a volatilidade da série, em particular o Escopo 2 (energia elétrica)?</div>
<div class="rq"><b>RQ3.</b> Que subsetores e gases explicam a variação líquida entre 2012 e 2024?</div>

<h2 id="metodo">2. Metodologia e pipeline de dados</h2>
<h3>2.1 Fonte e granularidade</h3>
<p>Os dados são a Tabela 3696 do Data.Rio/IPP, “Emissões de gases de efeito estufa (GEE) da Cidade do Rio de Janeiro”, em toneladas de CO₂ equivalente (t CO₂e), de 2012 a 2024 (versão de setembro de 2026). A unidade de observação é <i>subsetor × ano × componente</i>. O arquivo (<code>3696.xls</code>) tem duas abas com o mesmo inventário: <code>3696_Escopos</code> (Escopo 1, 2, 3 e total) e <code>3696_GEE</code> (CO₂, CH₄, N₂O e total). As emissões já vêm convertidas em CO₂e com os potenciais de aquecimento global do quinto relatório do IPCC (IPCC, 2014). As estimativas de 2012–2021 foram revisadas em 2024, conforme as notas da fonte.</p>
<h3>2.2 Tratamento</h3>
<ul>
  <li><b>Estrutura:</b> cada aba tem anos em um cabeçalho mesclado e componentes em outro. O ano é propagado com <code>ffill</code> e a tabela larga vira formato longo (4.056 linhas).</li>
  <li><b>Hierarquia:</b> as linhas são classificadas em <code>setor</code> (5), <code>subsetor</code> (31), <code>total</code> e <code>memo</code>. Os itens <i>memo</i> (geração para o Sistema Interligado Nacional e compostagem) pertencem ao inventário territorial, mas, pela metodologia GPC, <b>não somam no total</b>; são mantidos à parte para não gerar dupla contagem.</li>
  <li><b>Símbolos de ausência:</b> “-” (zero não resultante de arredondamento) e “(0)” viram 0; “...” (não aplicável) e “NE” (não estimado) viram <code>NaN</code>, sem imputação, porque nenhum método de preenchimento seria defensável para dados de inventário.</li>
  <li><b>Normalização:</b> remoção de notas de rodapé nos rótulos e correção de grafias (“Ferrroviário”, “Ceu”).</li>
  <li><b>Valores negativos mantidos:</b> reflorestamento e arborização urbana removem carbono e entram com sinal negativo.</li>
  <li><b>Validação:</b> a soma dos cinco setores reproduz o TOTAL publicado (diferença máxima de 0,00 t) e as partes por escopo e por gás somam o total de cada linha. Os arquivos brutos nunca são alterados e o log de decisões fica em <code>data/processed/etl_log.txt</code>.</li>
  <li><b>Métricas derivadas:</b> participação percentual, variação percentual, taxa de crescimento anual composta (CAGR) e coeficiente de variação (CV = desvio-padrão/média).</li>
</ul>
<p>Trechos centrais do pipeline (<code>src/etl.py</code>):</p>
<pre><code>{code['parse']}</code></pre>
<pre><code>{code['num']}</code></pre>
<pre><code>{code['valid']}</code></pre>

<h2 id="resultados">3. Resultados e discussão</h2>
<h3>3.1 RQ1 — Trajetória do total e composição setorial</h3>
<p>As emissões totais caíram de {fmt_mt(m['total_2012'])} Mt CO₂e em 2012 para {fmt_mt(m['total_2024'])} Mt em 2024 ({m['var_2012_2024_pct']:.1f}%; CAGR de {m['cagr_total_pct']:.2f}% ao ano). A série subiu até o pico de {fmt_mt(m['pico_valor'])} Mt em {m['pico_ano']}, e o nível de 2024 está {abs(m['var_2014_2024_pct']):.1f}% abaixo desse pico. Entre 2019 e 2020 houve queda de {abs(m['var_2019_2020_pct']):.1f}% (mínimo de {fmt_mt(m['min_valor'])} Mt) e, em 2021, recuperação de {m['var_2020_2021_pct']:.1f}%. Uma regressão linear simples indica tendência de {fmt_mt(m['tendencia_t_por_ano'])} Mt por ano (R² = {m['tendencia_r2']:.2f}, p = {m['tendencia_p']:.3f}); com apenas 13 observações autocorrelacionadas, vale como descrição da inclinação, não como inferência causal.</p>
<figure>
  <div id="g1" class="plot" role="img" aria-label="Barras empilhadas das emissões por setor de 2012 a 2024"></div>
  <figcaption><b>Figura 1.</b> Emissões por setor (interativo: use os botões para alternar entre valores absolutos e participação; clique na legenda para ocultar setores). Fonte: Data.Rio/IPP, Tabela 3696; elaboração própria.</figcaption>
</figure>
<p>A composição mudou: energia estacionária subiu de {m['participacao_pct']['2012']['Energia Estacionária']:.1f}% para {m['participacao_pct']['2024']['Energia Estacionária']:.1f}% do total, enquanto transportes recuaram de {m['participacao_pct']['2012']['Transportes']:.1f}% para {m['participacao_pct']['2024']['Transportes']:.1f}%. Esse movimento não indica crescimento da energia estacionária, que variou apenas {m['var_setor_2012_2024_pct']['Energia Estacionária']:+.1f}% no período. Ele resulta da queda de {abs(m['var_setor_2012_2024_pct']['Transportes']):.1f}% em transportes, que reduziu o denominador. Resíduos cresceram {m['var_setor_2012_2024_pct']['Resíduos']:.1f}% e processos industriais caíram {abs(m['var_setor_2012_2024_pct']['Processos Industriais e Uso de Produtos']):.1f}%. O setor agropecuário, florestal e de uso do solo dobrou, mas parte de uma base mínima (cerca de 0,1% a 0,2% do total).</p>
<div class="tw"><table>
<thead><tr><th>Setor</th><th>2012</th><th>2019</th><th>2024</th><th>Var. 2012–24</th><th>CV 2012–24</th></tr></thead>
<tbody>
{tabela_resumo(m)}
</tbody></table></div>
<p class="note">Tabela 1. Participação no total, variação e coeficiente de variação por setor.</p>
<figure>
  <img src="assets/fig2_participacao.png" alt="Barras horizontais com a participação de cada setor em 2012, 2019 e 2024" loading="lazy">
  <figcaption><b>Figura 2.</b> Composição setorial em 2012, 2019 e 2024.</figcaption>
</figure>
<p>Entre os dois maiores setores, transportes são o mais sensível a choques (CV de {m['cv_setor_pct']['Transportes']:.1f}%, contra {m['cv_setor_pct']['Energia Estacionária']:.1f}% da energia estacionária). A queda de 2020 é compatível com as restrições de mobilidade da pandemia de covid-19, e a recuperação posterior é parcial, o que as séries de aviação e transporte rodoviário (RQ3) detalham. Associar a queda à pandemia é uma interpretação de contexto; os dados do inventário não medem a causa.</p>

<h3>3.2 RQ2 — Volatilidade por escopo</h3>
<p>O Escopo 1 (emissões dentro do território) responde por entre {esc['2014']['Escopo 1']:.0f}% (2014) e {esc['2022']['Escopo 1']:.0f}% (2022) do total e é o componente mais estável (CV de {m['cv_escopo_pct']['Escopo 1']:.1f}%). O Escopo 3 oscila mais (CV de {m['cv_escopo_pct']['Escopo 3']:.1f}%) e cai de cerca de {esc['2014']['Escopo 3']:.0f}% do total em 2014 para {esc['2021']['Escopo 3']:.0f}% em 2021. O Escopo 2, ligado à eletricidade consumida, tem CV de {m['cv_escopo_pct']['Escopo 2']:.1f}%: atinge {fmt_mt(m['escopo2_max'][1])} Mt em {m['escopo2_max'][0]} ({esc['2014']['Escopo 2']:.1f}% do total) e apenas {fmt_mt(m['escopo2_min'][1])} Mt em {m['escopo2_min'][0]}.</p>
<figure>
  <div id="g2" class="plot" role="img" aria-label="Linhas das emissões por escopo de 2012 a 2024"></div>
  <figcaption><b>Figura 3.</b> Emissões por escopo, 2012–2024 (interativo).</figcaption>
</figure>
<p>Como o Escopo 2 depende do fator de emissão da rede elétrica, e não só do consumo da cidade, grande parte da sua oscilação deve refletir a matriz do sistema nacional naquele ano. Um indício nos próprios dados é a associação entre o Escopo 2 e a geração de energia elétrica para o Sistema Interligado Nacional (SIN) reportada como item informativo, com r = {m['corr_escopo2_sin']:.2f} (Figura 4). A correlação é moderada, e a relação não é linear nem estável no tempo (por exemplo, 2021 destoa). Portanto, o resultado sugere, sem comprovar, que o Escopo 2 é um indicador ruim de esforço local de eficiência e que metas urbanas devem distinguir reduções sob controle da cidade (Escopo 1) das induzidas pela rede.</p>
<figure>
  <img src="assets/fig3_escopos.png" alt="Barras empilhadas por escopo e dispersão entre Escopo 2 e geração para o SIN" loading="lazy">
  <figcaption><b>Figura 4.</b> À esquerda, emissões por escopo; à direita, Escopo 2 contra a geração para o SIN no território (cada ponto é um ano).</figcaption>
</figure>

<h3>3.3 RQ3 — Subsetores e gases por trás da redução líquida</h3>
<p>A redução líquida de {fmt_mt(abs(m['delta_total']))} Mt entre 2012 e 2024 é a soma de movimentos de sinais opostos. Os três maiores contribuintes de queda são aviação (−1,21 Mt; −37,9%), transporte rodoviário (−0,92 Mt; −17,1%) e produção de ferro e aço (−0,66 Mt; −28,8%), que juntos somam {fmt_mt(abs(m['soma_deltas_top3_queda']))} Mt, ou seja, mais que toda a redução líquida. O aterramento de resíduos (+0,38 Mt; +24,0%), as indústrias de energia (+0,19 Mt) e as indústrias de manufatura e construção (+0,16 Mt) compensam parte da queda. Na aviação, a queda já está presente antes da pandemia (de 3,20 Mt em 2012 para 2,29 Mt em 2019), logo não se explica apenas por 2020.</p>
<figure>
  <div class="ctrl"><label>De <select id="y0"></select></label><label>até <select id="y1"></select></label><span>Os 8 maiores recuos e aumentos entre os anos escolhidos</span></div>
  <div id="g3" class="plot" role="img" aria-label="Barras horizontais com a variação absoluta por subsetor entre dois anos escolhidos"></div>
  <figcaption><b>Figura 5.</b> Explorador de variações por subsetor (interativo; padrão 2012→2024). Verde indica redução e laranja, aumento.</figcaption>
</figure>
<p>Quanto aos gases, o CO₂ permanece dominante, mas perde participação: de {gas['2012']['CO2']:.1f}% (2012) para {gas['2024']['CO2']:.1f}% (2024), com queda absoluta de {abs(m['var_gas_2012_2024_pct']['CO2']):.1f}%. O metano cresce {m['var_gas_2012_2024_pct']['CH4']:.1f}% e sua participação sobe de {gas['2012']['CH4']:.1f}% para {gas['2024']['CH4']:.1f}%, em linha com o aumento do aterramento de resíduos, fonte típica de CH₄. O N₂O fica praticamente estável em termos absolutos ({m['var_gas_2012_2024_pct']['N2O']:+.1f}%) e responde por menos de 2% do total. Assim, a descarbonização observada é essencialmente de CO₂ (combustíveis), e a agenda de resíduos e metano ganha peso relativo.</p>
<figure>
  <img src="assets/fig4_gases.png" alt="Emissões por gás e participação de CH4 e N2O ao longo do tempo" loading="lazy">
  <figcaption><b>Figura 6.</b> Emissões por gás (esquerda) e participação de CH₄ e N₂O (direita).</figcaption>
</figure>

<h2 id="conclusao">4. Conclusão</h2>
<p><b>RQ1.</b> As emissões do Rio caíram {abs(m['var_2012_2024_pct']):.1f}% entre 2012 e 2024, com pico em {m['pico_ano']} e mínimo em {m['min_ano']}; energia estacionária e transportes concentram cerca de {m['participacao_pct']['2024']['Energia Estacionária'] + m['participacao_pct']['2024']['Transportes']:.0f}% do total. <b>RQ2.</b> O Escopo 2 é o mais volátil e se associa à geração do sistema elétrico nacional, o que o torna um indicador frágil do esforço local. <b>RQ3.</b> A redução líquida vem de aviação, transporte rodoviário e siderurgia, e o metano ganha participação por causa dos resíduos.</p>
<p><b>Limitações.</b> (i) São 13 pontos anuais, o que limita testes estatísticos; (ii) a série foi revisada em 2024 e pode ser revisada de novo; (iii) o inventário não traz causas, de modo que explicações como a pandemia ou a matriz elétrica são hipóteses de contexto; (iv) valores “NE” e “...” não foram imputados; (v) a análise é agregada para a cidade e não diferencia bairros ou fontes individuais.</p>
<p><b>Trabalhos futuros.</b> Cruzar a série com população, PIB municipal e fator de emissão da rede para calcular intensidades per capita e por unidade de PIB; decompor a variação do Escopo 2 em efeito consumo e efeito fator de emissão; e comparar o Rio com outras cidades signatárias do GPC.</p>

<h2 id="fair">5. Disponibilidade dos dados e declaração FAIR</h2>
<ul>
  <li><b>Findable:</b> repositório com <code>README.md</code>, palavras-chave, autoria, disciplina e semestre; dados brutos referenciados pelo <a href="{c['dados_url']}">link da fonte</a>.</li>
  <li><b>Accessible:</b> repositório público no GitHub; scripts rodam sem credenciais; artigo servido pelo GitHub Pages, com layout responsivo.</li>
  <li><b>Interoperable:</b> dados processados em <code>.csv.gz</code> (formato aberto) e <code>data/data_dictionary.md</code> descrevendo cada variável.</li>
  <li><b>Reusable:</b> licença MIT (código) e CC BY 4.0 (dados e texto); <code>requirements.txt</code> com versões fixas.</li>
</ul>
<p>Para reproduzir todo o pipeline:</p>
<pre><code>git clone {c['repo_url']}.git
cd {c['repo_url'].rsplit('/', 1)[-1]}
python -m venv .venv &amp;&amp; source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python -m src.etl          # data/raw/3696.xls -&gt; data/processed/*.csv.gz
python -m src.analysis     # figuras e métricas em docs/assets/
python -m src.build_site   # regenera docs/index.html</code></pre>

<h2 id="refs">6. Referências</h2>
<ol class="refs">
<li>HUNTER, J. D. Matplotlib: a 2D graphics environment. <i>Computing in Science &amp; Engineering</i>, v. 9, n. 3, p. 90–95, 2007.</li>
<li>INTERGOVERNMENTAL PANEL ON CLIMATE CHANGE (IPCC). <i>Climate Change 2014: Synthesis Report</i>. Genebra: IPCC, 2014.</li>
<li>McKINNEY, W. Data structures for statistical computing in Python. In: PYTHON IN SCIENCE CONFERENCE, 9., 2010. <i>Proceedings…</i>, p. 56–61, 2010.</li>
<li>PLOTLY TECHNOLOGIES INC. <i>Collaborative data science</i>. Montreal: Plotly Technologies Inc., 2015. Disponível em: https://plot.ly.</li>
<li>RIO DE JANEIRO (Município). Instituto Municipal de Urbanismo Pereira Passos (IPP). <i>Emissões de gases de efeito estufa (GEE) da Cidade do Rio de Janeiro, em t CO₂e — 2012 a 2024</i> (Tabela 3696). Data.Rio, set. 2026. Disponível em: <a href="{c['dados_url']}">{c['dados_url']}</a>. Acesso em: 13 nov. 2026.</li>
<li>WILKINSON, M. D. et al. The FAIR Guiding Principles for scientific data management and stewardship. <i>Scientific Data</i>, v. 3, art. 160018, 2016.</li>
<li>WORLD RESOURCES INSTITUTE (WRI); C40 CITIES CLIMATE LEADERSHIP GROUP; ICLEI. <i>Global Protocol for Community-Scale Greenhouse Gas Emission Inventories (GPC)</i>: an accounting and reporting standard for cities. Washington, DC: WRI, 2014.</li>
</ol>

<footer>
  {html.escape(c['disciplina'])} · {html.escape(c['instituicao'])} · {html.escape(c['semestre'])}.<br>
  Texto e dados processados sob licença <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>; código sob licença MIT. Dados originais: Data.Rio/IPP.
</footer>
</div>
<script>
{JS.replace('__DATA__', json.dumps(dados, ensure_ascii=False))}
</script>
<noscript><p class="note" style="text-align:center">Os gráficos interativos exigem JavaScript. As Figuras 2, 4 e 6 estão disponíveis como imagens.</p></noscript>
<!-- resumo: {n_palavras} palavras -->
</body>
</html>
"""


def decimal_br(doc: str) -> str:
    """Troca ponto decimal por vírgula nos textos (fora de <pre>, <script>, <style> e atributos)."""
    partes = re.split(r"(<pre>.*?</pre>|<script.*?</script>|<style>.*?</style>)", doc, flags=re.S)
    def texto(m: re.Match) -> str:
        bruto = m.group(1)
        num = re.match(r"\d\.\d ", bruto)  # numeração de seção (2.1, 3.3...) fica como está
        pre, resto = (bruto[:3], bruto[3:]) if num else ("", bruto)
        t = re.sub(r"(?<=\d)\.(?=\d)", ",", resto.replace("CC BY 4.0", "CC BY 4§0"))
        return ">" + pre + t.replace("4§0", "4.0") + "<"
    out = []
    for i, parte in enumerate(partes):
        out.append(parte if i % 2 else re.sub(r">([^<>]*)<", texto, parte))
    return "".join(out)


def main() -> None:
    OUT.write_text(decimal_br(montar_html()), encoding="utf-8")
    print(f"Artigo gerado em {OUT}")


if __name__ == "__main__":
    main()
