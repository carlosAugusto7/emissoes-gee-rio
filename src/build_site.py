"""
Gera docs/index.html (artigo acadêmico estático e interativo) a partir dos dados processados.

Uso:
    python -m src.build_site

Os dados dos gráficos (Plotly.js) são embutidos no HTML: a página não depende de servidor.
"""
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
    "autores": ["Carlos Augusto Ferreira Souza", "Wilson da Silva Prata Junior"],
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
:root{--bg:#fff;--fg:#1d2327;--mut:#5b6670;--line:#dfe4e8;--acc:#0b5cab;--acc2:#3b8de0;--card:#f6f8fa;--code:#0f1720;--codefg:#e6edf3;--shadow:0 6px 24px rgba(15,23,32,.07);--bar:rgba(255,255,255,.82)}
[data-theme="dark"]{--bg:#12161a;--fg:#e6e9ec;--mut:#9aa6b0;--line:#2a3138;--acc:#6db3ff;--acc2:#2f7fd6;--card:#1a2025;--shadow:0 6px 24px rgba(0,0,0,.35);--bar:rgba(18,22,26,.82)}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:70px}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.68 Georgia,'Times New Roman',serif;transition:background .25s,color .25s}
.wrap{max-width:880px;margin:0 auto;padding:0 20px 80px}
/* barra superior */
.top{position:sticky;top:0;z-index:50;background:var(--bar);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.top-in{max-width:1100px;margin:0 auto;padding:0 16px;height:52px;display:flex;align-items:center;gap:14px;font:600 13.5px system-ui,sans-serif}
.top .brand{color:var(--fg);text-decoration:none;white-space:nowrap;font-weight:700}
.top nav{display:flex;gap:2px;margin-left:auto;overflow-x:auto;scrollbar-width:none}
.top nav a{color:var(--mut);text-decoration:none;padding:6px 10px;border-radius:6px;white-space:nowrap;transition:.15s}
.top nav a:hover{color:var(--fg);background:var(--card)}.top nav a.on{color:var(--acc);background:var(--card)}
.tbtn{border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:8px;width:34px;height:34px;cursor:pointer;font-size:16px;flex:none}
.tbtn:hover{border-color:var(--acc)}
#prog{position:absolute;left:0;bottom:-1px;height:3px;width:0;background:linear-gradient(90deg,var(--acc2),var(--acc));transition:width .08s}
/* cabeçalho */
header{padding:54px 0 28px}
header .kicker{font:700 12.5px/1 system-ui,sans-serif;letter-spacing:.1em;text-transform:uppercase;color:var(--acc)}
h1{font-size:clamp(1.6rem,4.4vw,2.3rem);line-height:1.22;margin:14px 0 18px;letter-spacing:-.01em}
.autores{font:16px/1.5 system-ui,sans-serif}.afil{font:14px/1.55 system-ui,sans-serif;color:var(--mut);margin-top:6px}
.badges{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px;font:600 12.5px/1 system-ui,sans-serif}
.badge{display:inline-block;padding:7px 11px;border-radius:999px;background:var(--card);border:1px solid var(--line);color:var(--fg);text-decoration:none;transition:.15s}
a.badge:hover{border-color:var(--acc);transform:translateY(-1px)}
.badge.gh{background:#24292f;color:#fff;border-color:#24292f}
/* KPIs */
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:26px 0 6px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 14px 12px;transition:.2s}
.kpi:hover{transform:translateY(-3px);box-shadow:var(--shadow);border-color:var(--acc)}
.kpi b{display:block;font:700 1.7rem/1.1 Georgia,serif;color:var(--acc);letter-spacing:-.02em}
.kpi span{display:block;font:12.5px/1.35 system-ui,sans-serif;color:var(--mut);margin-top:6px}
@media(max-width:700px){.kpis{grid-template-columns:repeat(2,1fr)}.top nav{display:none}.top .brand{flex:1;overflow:hidden;text-overflow:ellipsis}}
/* texto */
h2{font-size:1.45rem;margin:52px 0 8px;padding-top:10px;letter-spacing:-.01em}
h2::before{content:"";display:block;width:34px;height:3px;border-radius:2px;background:linear-gradient(90deg,var(--acc2),var(--acc));margin-bottom:12px}
h3{font-size:1.14rem;margin:30px 0 4px}p{margin:.7em 0}a{color:var(--acc)}
.abstract{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--acc);border-radius:10px;padding:4px 22px 16px;margin:26px 0}
.abstract h2{margin-top:14px;font-size:1.1rem}.abstract h2::before{display:none}.kw{font:14px/1.5 system-ui,sans-serif;color:var(--mut)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}.chips span{font:12.5px system-ui,sans-serif;background:var(--bg);border:1px solid var(--line);border-radius:999px;padding:4px 10px;color:var(--mut)}
.rq{border-left:4px solid var(--acc);padding:6px 16px;margin:12px 0;background:var(--card);border-radius:0 8px 8px 0}
.take{margin:22px 0;padding:14px 18px;border-radius:10px;background:linear-gradient(135deg,rgba(59,141,224,.12),rgba(59,141,224,.03));border:1px solid var(--line)}
.take b.t{display:block;font:700 11.5px system-ui,sans-serif;letter-spacing:.1em;text-transform:uppercase;color:var(--acc);margin-bottom:4px}
/* figuras */
figure{margin:28px 0;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 14px 10px;box-shadow:var(--shadow)}
figure img{max-width:100%;height:auto;border-radius:6px;background:#fff}
figcaption{font:14px/1.5 system-ui,sans-serif;color:var(--mut);margin-top:6px}
.plot{width:100%;min-height:360px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:700px){.pair{grid-template-columns:1fr}}
.ctrl{font:14px system-ui,sans-serif;margin:2px 0 8px;display:flex;gap:12px;flex-wrap:wrap;align-items:center}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:9px;overflow:hidden;background:var(--bg)}
.seg button{border:0;background:none;color:var(--mut);font:600 13px system-ui,sans-serif;padding:7px 13px;cursor:pointer;transition:.15s}
.seg button+button{border-left:1px solid var(--line)}.seg button:hover{color:var(--fg)}
.seg button.on{background:var(--acc);color:#fff}
select{font:600 13px system-ui,sans-serif;padding:6px 8px;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:7px}
/* código e tabelas */
.code{position:relative}.copy{position:absolute;top:8px;right:8px;border:1px solid #3a444e;background:#1b2530;color:#cdd6de;border-radius:6px;font:600 11.5px system-ui,sans-serif;padding:4px 9px;cursor:pointer;opacity:.0;transition:.15s}
.code:hover .copy,.copy:focus{opacity:1}
pre{background:var(--code);color:var(--codefg);padding:14px 16px;border-radius:10px;overflow-x:auto;font:13px/1.55 ui-monospace,Menlo,Consolas,monospace;margin:12px 0}
code{font:.88em ui-monospace,Menlo,Consolas,monospace;background:var(--card);padding:1px 5px;border-radius:4px}pre code{background:none;padding:0}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:10px}table{border-collapse:collapse;width:100%;font:14px/1.45 system-ui,sans-serif}
th,td{border-bottom:1px solid var(--line);padding:9px 12px;text-align:right}th:first-child,td:first-child{text-align:left}th{background:var(--card);cursor:pointer;user-select:none;white-space:nowrap}
th:hover{color:var(--acc)}tbody tr:hover{background:var(--card)}tbody tr:last-child td{border-bottom:0}
.neg{color:#0a9b72}.pos{color:#d55e00}
.note{font:14px/1.5 system-ui,sans-serif;color:var(--mut)}
ul{padding-left:1.2em}li{margin:.3em 0}
ol.refs{padding-left:1.3em;font-size:15.5px}ol.refs li{margin:.5em 0}
footer{margin-top:56px;padding-top:16px;border-top:1px solid var(--line);font:13px/1.55 system-ui,sans-serif;color:var(--mut)}
#up{position:fixed;right:18px;bottom:18px;width:42px;height:42px;border-radius:50%;border:1px solid var(--line);background:var(--card);color:var(--fg);box-shadow:var(--shadow);cursor:pointer;font-size:18px;opacity:0;pointer-events:none;transition:.2s}
#up.show{opacity:1;pointer-events:auto}
.reveal{opacity:0;transform:translateY(14px);transition:opacity .6s ease,transform .6s ease}.reveal.in{opacity:1;transform:none}
@media (prefers-reduced-motion:reduce){.reveal{opacity:1;transform:none;transition:none}html{scroll-behavior:auto}}
@media (max-width:560px){body{font-size:16px}h2{font-size:1.28rem}.wrap{padding:0 16px 70px}}
@media print{.top,#up,.copy,.seg,.ctrl{display:none}.reveal{opacity:1;transform:none}figure{box-shadow:none}}
"""

JS = """
const D = __DATA__;
const $ = (s, r) => (r || document).querySelector(s), $$ = (s, r) => [...(r || document).querySelectorAll(s)];
const root = document.documentElement;
const Mt = v => v / 1e6;
const pt = (v, d) => v.toLocaleString('pt-BR', {minimumFractionDigits: d, maximumFractionDigits: d});
const S = {g1: 'abs', g2: 'abs', yA: 2012, yB: 2024};

/* ---------- tema ---------- */
function setTheme(t, save) {
  root.dataset.theme = t;
  $('#theme').textContent = t === 'dark' ? '☀' : '☾';
  $('#theme').setAttribute('aria-label', t === 'dark' ? 'Mudar para tema claro' : 'Mudar para tema escuro');
  if (save) { try { localStorage.setItem('tema', t); } catch (e) {} }
  if (window.Plotly) renderAll();
}
(function () {
  let t = null;
  try { t = localStorage.getItem('tema'); } catch (e) {}
  if (!t) t = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  root.dataset.theme = t;
})();

/* ---------- gráficos ---------- */
function col() {
  const cs = getComputedStyle(root);
  return {fg: cs.getPropertyValue('--fg').trim(), grid: cs.getPropertyValue('--line').trim(), mut: cs.getPropertyValue('--mut').trim(), acc: cs.getPropertyValue('--acc').trim()};
}
function base(extra) {
  const c = col();
  return Object.assign({
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
    font: {family: 'system-ui,sans-serif', color: c.fg, size: 13},
    margin: {l: 58, r: 14, t: 16, b: 46},
    xaxis: {gridcolor: c.grid, zeroline: false}, yaxis: {gridcolor: c.grid, zeroline: false},
    legend: {orientation: 'h', y: -0.2}, hoverlabel: {font: {family: 'system-ui,sans-serif'}}
  }, extra || {});
}
const cfg = {responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d']};
const plot = (id, tr, lay) => Plotly.react(id, tr, lay, cfg);

function g1() {
  const pct = S.g1 === 'pct';
  const tr = D.setores.map(s => ({type: 'bar', name: s.nome, x: D.anos, y: s.valores.map(Mt), marker: {color: s.cor},
    hovertemplate: '%{x}: %{y:.2f} Mt CO₂e<extra>' + s.nome + '</extra>'}));
  const c = col();
  plot('g1', tr, base({barmode: 'stack', barnorm: pct ? 'percent' : '',
    xaxis: {dtick: 1, gridcolor: c.grid}, yaxis: {title: pct ? '% do total' : 'Milhões de t CO₂e', gridcolor: c.grid}}));
}
function g2() {
  const mode = S.g2, c = col();
  const tot = D.anos.map((_, i) => D.escopos.reduce((a, s) => a + s.valores[i], 0));
  const tr = D.escopos.map(s => {
    let y = s.valores.map(Mt), t = 'Mt';
    if (mode === 'share') { y = s.valores.map((v, i) => v / tot[i] * 100); t = '%'; }
    if (mode === 'idx') { y = s.valores.map(v => v / s.valores[0] * 100); t = 'índice'; }
    return {type: 'scatter', mode: 'lines+markers', name: s.nome, x: D.anos, y, line: {color: s.cor, width: 2.8}, marker: {size: 7},
      hovertemplate: '%{x}: %{y:.1f} ' + t + '<extra>' + s.nome + '</extra>'};
  });
  const yt = {abs: 'Milhões de t CO₂e', share: '% do total', idx: 'Índice (2012 = 100)'}[mode];
  plot('g2', tr, base({xaxis: {dtick: 1, gridcolor: c.grid}, yaxis: {title: yt, gridcolor: c.grid, rangemode: 'tozero'}}));
}
function gShare() {
  const c = col(), iA = D.anos.indexOf(S.yA), iB = D.anos.indexOf(S.yB);
  const part = i => D.setores.map(s => s.valores[i] / D.setores.reduce((a, q) => a + q.valores[i], 0) * 100);
  const nomes = D.setores.map(s => s.nome.replace('Processos Industriais e Uso de Produtos', 'Processos industriais').replace('Agropecuária, Floresta e Uso do Solo', 'Agro, floresta e solo'));
  const mk = (i, y, color) => ({type: 'bar', orientation: 'h', name: String(y), y: nomes, x: part(i), marker: {color},
    text: part(i).map(v => pt(v, 1) + '%'), textposition: 'outside', cliponaxis: false, hovertemplate: '%{y}: %{x:.1f}% (' + y + ')<extra></extra>'});
  plot('gs', [mk(iA, S.yA, '#8db8e6'), mk(iB, S.yB, '#0b5cab')],
    base({barmode: 'group', margin: {l: 150, r: 40, t: 10, b: 46}, xaxis: {title: 'Participação no total (%)', range: [0, 58], gridcolor: c.grid},
      yaxis: {autorange: 'reversed', automargin: true}, height: 380}));
}
function g3() {
  const c = col();
  const tr = [{type: 'scatter', mode: 'markers+text', x: D.sin.map(Mt), y: D.escopos[1].valores.map(Mt), text: D.anos.map(a => String(a).slice(2)),
    textposition: 'top right', textfont: {size: 11, color: c.mut}, marker: {size: 11, color: '#D55E00', line: {color: '#fff', width: 1}}, name: 'Anos',
    hovertemplate: '%{customdata}<br>SIN: %{x:.2f} Mt · Escopo 2: %{y:.2f} Mt<extra></extra>', customdata: D.anos}];
  const x = D.sin.map(Mt), y = D.escopos[1].valores.map(Mt), n = x.length;
  const mx = x.reduce((a, b) => a + b) / n, my = y.reduce((a, b) => a + b) / n;
  let sxy = 0, sxx = 0, syy = 0; x.forEach((v, i) => { sxy += (v - mx) * (y[i] - my); sxx += (v - mx) ** 2; syy += (y[i] - my) ** 2; });
  const b1 = sxy / sxx, b0 = my - b1 * mx, r = sxy / Math.sqrt(sxx * syy);
  const x0 = Math.min(...x), x1 = Math.max(...x);
  tr.push({type: 'scatter', mode: 'lines', x: [x0, x1], y: [b0 + b1 * x0, b0 + b1 * x1], line: {dash: 'dash', color: c.mut, width: 1.5}, hoverinfo: 'skip', name: 'Tendência linear'});
  plot('g3', tr, base({xaxis: {title: 'Geração para o SIN no território (Mt CO₂e)', gridcolor: c.grid}, yaxis: {title: 'Escopo 2 (Mt CO₂e)', gridcolor: c.grid},
    annotations: [{xref: 'paper', yref: 'paper', x: 0.02, y: 0.98, showarrow: false, text: 'r = ' + pt(r, 2), font: {size: 15, color: c.acc}}]}));
}
function g4() {
  const c = col(), cores = {CO2: '#555', CH4: '#E69F00', N2O: '#CC79A7'};
  const nomes = {CO2: 'CO₂', CH4: 'CH₄', N2O: 'N₂O'};
  const tr = Object.keys(cores).map(k => ({type: 'scatter', mode: 'lines', stackgroup: 'g', name: nomes[k], x: D.anos, y: D.gases[k].map(Mt),
    line: {color: cores[k], width: 0.5}, fillcolor: cores[k], hovertemplate: '%{x}: %{y:.2f} Mt<extra>' + nomes[k] + '</extra>'}));
  plot('g4', tr, base({xaxis: {dtick: 2, gridcolor: c.grid}, yaxis: {title: 'Milhões de t CO₂e', gridcolor: c.grid}}));
  const sh = k => D.anos.map((_, i) => D.gases[k][i] / D.gases.Total[i] * 100);
  const tr2 = ['CH4', 'N2O'].map(k => ({type: 'scatter', mode: 'lines+markers', name: nomes[k], x: D.anos, y: sh(k), line: {color: cores[k], width: 2.8},
    hovertemplate: '%{x}: %{y:.2f}%<extra>' + nomes[k] + '</extra>'}));
  plot('g5', tr2, base({xaxis: {dtick: 2, gridcolor: c.grid}, yaxis: {title: 'Participação no total (%)', gridcolor: c.grid, rangemode: 'tozero'}}));
}
function g6() {
  const c = col(), a = S.yA, b = S.yB, ia = D.anos.indexOf(a), ib = D.anos.indexOf(b);
  const rows = D.subsetores.map(s => ({n: s.nome, d: Mt(s.valores[ib] - s.valores[ia])})).filter(r => !isNaN(r.d)).sort((p, q) => p.d - q.d);
  let sel = rows.slice(0, 8).concat(rows.slice(-8));
  sel = sel.filter((r, i, arr) => arr.findIndex(x => x.n === r.n) === i);
  const lab = n => n.length > 44 ? n.slice(0, 42) + '…' : n;
  plot('g6', [{type: 'bar', orientation: 'h', x: sel.map(r => r.d), y: sel.map(r => lab(r.n)), customdata: sel.map(r => r.n),
    marker: {color: sel.map(r => r.d < 0 ? '#009E73' : '#D55E00')}, text: sel.map(r => (r.d > 0 ? '+' : '') + pt(r.d, 2)), textposition: 'outside', cliponaxis: false,
    hovertemplate: '%{customdata}<br>%{x:+.3f} Mt CO₂e<extra></extra>'}],
    base({margin: {l: 250, r: 50, t: 10, b: 50}, xaxis: {title: 'Variação ' + a + '→' + b + ' (milhões de t CO₂e)', gridcolor: c.grid, zeroline: true, zerolinecolor: c.fg},
      yaxis: {automargin: true, tickfont: {size: 11.5}}, height: 540}));
}
function renderAll() { g1(); g2(); gShare(); g3(); g4(); g6(); }

/* ---------- controles ---------- */
$$('.seg').forEach(seg => seg.addEventListener('click', e => {
  const btn = e.target.closest('button'); if (!btn) return;
  $$('button', seg).forEach(b => b.classList.toggle('on', b === btn));
  S[seg.dataset.for] = btn.dataset.m; (seg.dataset.for === 'g1' ? g1 : g2)();
}));
function fillYears(idA, idB, fn) {
  const a = $(idA), b = $(idB);
  D.anos.forEach(y => { a.add(new Option(y, y)); b.add(new Option(y, y)); });
  a.value = S.yA; b.value = S.yB;
  [a, b].forEach(el => el.addEventListener('change', () => {
    S.yA = +a.value; S.yB = +b.value;
    ['#sa', '#sb', '#y0', '#y1'].forEach((id, k) => { $(id).value = k % 2 ? S.yB : S.yA; });
    gShare(); g6();
  }));
}
fillYears('#sa', '#sb'); fillYears('#y0', '#y1');

/* ---------- navegação, progresso, revelações ---------- */
const prog = $('#prog'), up = $('#up');
addEventListener('scroll', () => {
  const h = root.scrollHeight - innerHeight;
  prog.style.width = (h > 0 ? scrollY / h * 100 : 0) + '%';
  up.classList.toggle('show', scrollY > 700);
}, {passive: true});
up.onclick = () => scrollTo({top: 0, behavior: 'smooth'});
const links = $$('.top nav a');
const spy = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) links.forEach(a => a.classList.toggle('on', a.getAttribute('href') === '#' + e.target.id));
}), {rootMargin: '-45% 0px -50% 0px'});
$$('main [id]').forEach(el => { if (links.some(a => a.getAttribute('href') === '#' + el.id)) spy.observe(el); });
const rev = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); rev.unobserve(e.target); } }), {threshold: .08});
$$('.reveal').forEach(el => rev.observe(el));

/* contadores dos indicadores */
const cnt = new IntersectionObserver(es => es.forEach(e => {
  if (!e.isIntersecting) return; cnt.unobserve(e.target);
  const el = e.target, v = parseFloat(el.dataset.v), d = +el.dataset.d, suf = el.dataset.s || '', t0 = performance.now();
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { el.textContent = pt(v, d) + suf; return; }
  (function f(t) { const k = Math.min(1, (t - t0) / 1100), ease = 1 - Math.pow(1 - k, 3); el.textContent = pt(v * ease, d) + suf; if (k < 1) requestAnimationFrame(f); })(t0);
}), {threshold: .6});
$$('.kpi b').forEach(el => cnt.observe(el));

/* copiar código e ordenar tabela */
$$('.code').forEach(w => {
  const b = document.createElement('button'); b.className = 'copy'; b.textContent = 'Copiar';
  b.onclick = () => navigator.clipboard.writeText($('pre', w).innerText).then(() => { b.textContent = 'Copiado ✓'; setTimeout(() => b.textContent = 'Copiar', 1400); });
  w.appendChild(b);
});
$$('th').forEach((th, i) => th.addEventListener('click', () => {
  const tb = th.closest('table').tBodies[0], rows = [...tb.rows], asc = th.dataset.asc !== '1';
  const num = s => parseFloat(s.replace('%', '').replace('+', '').replace(',', '.'));
  rows.sort((a, b) => {
    const x = a.cells[i].textContent.trim(), y = b.cells[i].textContent.trim();
    return (i === 0 ? x.localeCompare(y) : num(x) - num(y)) * (asc ? 1 : -1);
  });
  rows.filter(r => !r.classList.contains('tot')).forEach(r => tb.insertBefore(r, tb.querySelector('.tot')));
  $$('th', th.parentNode).forEach(t => t.dataset.asc = ''); th.dataset.asc = asc ? '1' : '0';
}));
$('#theme').onclick = () => setTheme(root.dataset.theme === 'dark' ? 'light' : 'dark', true);

/* o Plotly carrega com "defer"; desenha quando estiver disponível */
function start() { if (window.Plotly) { setTheme(root.dataset.theme, false); } else setTimeout(start, 80); }
start();
"""


def fmt_mt(x: float) -> str:
    return f"{x / 1e6:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def montar_dados() -> dict:
    df = analysis.carregar()
    s = analysis.tabela_setores(df)
    esc = analysis.tabela_total(df, "escopo")
    gas = analysis.tabela_total(df, "gas")
    sub = analysis.tabela_subsetores(df)
    sin = analysis.serie_sin(df)
    anos = [int(a) for a in s.index]
    return {
        "anos": anos,
        "setores": [{"nome": k, "cor": analysis.COR_SETOR[k], "valores": [float(v) for v in s[k]]} for k in analysis.SETORES],
        "escopos": [{"nome": k, "cor": analysis.COR_ESCOPO[k], "valores": [float(v) for v in esc[k]]} for k in analysis.COR_ESCOPO],
        "gases": {k: [float(v) for v in gas[k]] for k in ["CO2", "CH4", "N2O", "Total"]},
        "sin": [float(sin[a]) for a in anos],
        "subsetores": [
            {"nome": k, "valores": [None if v != v else float(v) for v in sub.loc[k, anos]]} for k in sub.index
        ],
    }


def tabela_resumo(m: dict) -> str:
    def cls(v: float) -> str:
        return "neg" if v < 0 else "pos"
    linhas = []
    for k in analysis.SETORES:
        p = m["participacao_pct"]
        v = m["var_setor_2012_2024_pct"][k]
        linhas.append(
            f"<tr><td>{html.escape(k)}</td><td>{p['2012'][k]:.1f}%</td><td>{p['2019'][k]:.1f}%</td><td>{p['2024'][k]:.1f}%</td>"
            f"<td class=\"{cls(v)}\">{v:+.1f}%</td><td>{m['cv_setor_pct'][k]:.1f}%</td></tr>"
        )
    linhas.append(
        f"<tr class=\"tot\"><td><b>Total</b></td><td>100%</td><td>100%</td><td>100%</td>"
        f"<td class=\"{cls(m['var_2012_2024_pct'])}\"><b>{m['var_2012_2024_pct']:+.1f}%</b></td><td>{m['cv_total_pct']:.1f}%</td></tr>"
    )
    return "\n".join(linhas)


def montar_html() -> str:
    c = CONFIG
    m = json.loads((analysis.ASSETS / "metrics.json").read_text(encoding="utf-8"))
    dados = montar_dados()
    esc = m["escopo_participacao_pct"]
    gas = m["gas_participacao_pct"]
    pp = m["participacao_pct"]
    autores = ", ".join(html.escape(a) for a in c["autores"])
    code = {k: html.escape(v) for k, v in SNIPPETS.items()}
    en_tr = pp["2024"]["Energia Estacionária"] + pp["2024"]["Transportes"]

    resumo = (
        "As cidades precisam de inventários de gases de efeito estufa (GEE) para orientar metas de mitigação, mas séries "
        "publicadas em planilhas dificultam a análise reprodutível. Este trabalho constrói um pipeline determinístico em Python "
        "que converte a Tabela 3696 do Data.Rio/IPP, com as emissões da cidade do Rio de Janeiro entre 2012 e 2024 segundo a "
        "metodologia GPC, em um conjunto de dados longo, validado e aberto, e o explora por setor, escopo e gás. As emissões "
        f"totais passaram de {fmt_mt(m['total_2012'])} Mt CO₂e em 2012 para {fmt_mt(m['total_2024'])} Mt em 2024 "
        f"({m['var_2012_2024_pct']:.1f}%), com pico em {m['pico_ano']} e mínimo em {m['min_ano']}. Energia estacionária e transportes "
        f"concentram cerca de {en_tr:.0f}% do total. "
        f"O Escopo 2 (eletricidade) é o componente mais volátil (coeficiente de variação de {m['cv_escopo_pct']['Escopo 2']:.0f}%, contra "
        f"{m['cv_escopo_pct']['Escopo 1']:.0f}% do Escopo 1) e se associa moderadamente à geração para o sistema elétrico nacional. A "
        "redução líquida decorre sobretudo da aviação, do transporte rodoviário e da siderurgia, parcialmente compensada pelo aterramento "
        f"de resíduos; a participação do metano subiu de {gas['2012']['CH4']:.1f}% para {gas['2024']['CH4']:.1f}%. "
        "Discutem-se limitações da série e propostas de trabalhos futuros."
    )
    n_palavras = len(resumo.split())

    kpis = [
        (m["var_2012_2024_pct"], 1, "%", "variação do total entre 2012 e 2024"),
        (m["pico_valor"] / 1e6, 2, " Mt", f"pico de emissões, em {m['pico_ano']}"),
        (en_tr, 0, "%", "do total vem de energia estacionária e transportes (2024)"),
        (m["cv_escopo_pct"]["Escopo 2"], 0, "%", "coeficiente de variação do Escopo 2 (eletricidade)"),
    ]
    kpi_html = "".join(
        f'<div class="kpi reveal"><b data-v="{v:.4f}" data-d="{d}" data-s="{s}">0</b><span>{t}</span></div>' for v, d, s, t in kpis
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(c['titulo'])}</title>
<meta name="description" content="Análise reprodutível das emissões de GEE da cidade do Rio de Janeiro (2012–2024) a partir da Tabela 3696 do Data.Rio/IPP.">
<meta name="author" content="{autores}">
<meta name="keywords" content="emissões de gases de efeito estufa, inventário GPC, Rio de Janeiro, análise exploratória de dados, FAIR">
<meta name="theme-color" content="#0b5cab">
<link rel="license" href="https://creativecommons.org/licenses/by/4.0/">
<script>try{{var t=localStorage.getItem('tema')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.dataset.theme=t}}catch(e){{}}</script>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" onerror="this.onerror=null;this.src='https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js'" defer></script>
<style>{CSS}</style>
<noscript><style>.reveal{{opacity:1;transform:none}}</style></noscript>
</head>
<body>
<div class="top"><div class="top-in">
  <a class="brand" href="#topo">Emissões de GEE · Rio de Janeiro</a>
  <nav aria-label="Seções">
    <a href="#resumo">Resumo</a><a href="#intro">Introdução</a><a href="#metodo">Metodologia</a><a href="#resultados">Resultados</a>
    <a href="#conclusao">Conclusão</a><a href="#fair">FAIR</a><a href="#refs">Referências</a>
  </nav>
  <button class="tbtn" id="theme" aria-label="Alternar tema">☾</button>
  <div id="prog"></div>
</div></div>
<div class="wrap" id="topo">
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
  <div class="kpis">{kpi_html}</div>
</header>

<main>
<section class="abstract reveal" id="resumo">
  <h2>Resumo</h2>
  <p>{resumo}</p>
  <p class="kw"><b>Palavras-chave:</b></p>
  <div class="chips"><span>emissões de gases de efeito estufa</span><span>inventário GPC</span><span>cidade do Rio de Janeiro</span><span>análise exploratória</span><span>ciência aberta (FAIR)</span></div>
</section>

<section id="intro">
<h2>1. Introdução</h2>
<p>Cidades concentram grande parte das emissões antrópicas de gases de efeito estufa e, ao mesmo tempo, dispõem de instrumentos de política local (uso do solo, mobilidade, resíduos, edificações) para reduzi-las. O Global Protocol for Community-Scale Greenhouse Gas Emission Inventories (GPC) padronizou a contabilidade urbana de GEE em setores e em três escopos: emissões dentro do território (Escopo 1), emissões associadas à energia da rede consumida na cidade (Escopo 2) e emissões que ocorrem fora do território por atividades nele realizadas (Escopo 3) (WRI; C40; ICLEI, 2014).</p>
<p>O Instituto Municipal de Urbanismo Pereira Passos (IPP) publica no portal Data.Rio a série anual de emissões do Rio de Janeiro. A série traz detalhes valiosos, mas vem em planilha com cabeçalhos em dois níveis, itens informativos que não somam no total e símbolos de dado ausente, o que dificulta a reutilização direta. Este trabalho trata a tabela como um problema de engenharia de dados e, a partir dela, busca responder:</p>
<div class="rq reveal"><b>RQ1.</b> Como evoluíram as emissões totais do Rio entre 2012 e 2024 e como mudou a composição setorial?</div>
<div class="rq reveal"><b>RQ2.</b> Que componentes, por escopo, explicam a volatilidade da série, em particular o Escopo 2 (energia elétrica)?</div>
<div class="rq reveal"><b>RQ3.</b> Que subsetores e gases explicam a variação líquida entre 2012 e 2024?</div>
</section>

<section id="metodo">
<h2>2. Metodologia e pipeline de dados</h2>
<h3>2.1 Fonte e granularidade</h3>
<p>Os dados são a Tabela 3696 do Data.Rio/IPP, “Emissões de gases de efeito estufa (GEE) da Cidade do Rio de Janeiro”, em toneladas de CO₂ equivalente (t CO₂e), de 2012 a 2024 (versão de setembro de 2026). A unidade de observação é <i>subsetor × ano × componente</i>. O arquivo (<code>3696.xls</code>) tem duas abas com o mesmo inventário: <code>3696_Escopos</code> (Escopo 1, 2, 3 e total) e <code>3696_GEE</code> (CO₂, CH₄, N₂O e total). As emissões já vêm convertidas em CO₂e com os potenciais de aquecimento global do quinto relatório do IPCC (IPCC, 2014). As estimativas de 2012–2021 foram revisadas em 2024, conforme as notas da fonte.</p>
<h3>2.2 Tratamento</h3>
<ul>
  <li><b>Estrutura:</b> cada aba tem anos em um cabeçalho mesclado e componentes em outro. O ano é propagado com <code>ffill</code> e a tabela larga vira formato longo (4056 linhas).</li>
  <li><b>Hierarquia:</b> as linhas são classificadas em <code>setor</code> (5), <code>subsetor</code> (31), <code>total</code> e <code>memo</code>. Os itens <i>memo</i> (geração para o Sistema Interligado Nacional e compostagem) pertencem ao inventário territorial, mas, pela metodologia GPC, <b>não somam no total</b>; são mantidos à parte para não gerar dupla contagem.</li>
  <li><b>Símbolos de ausência:</b> “-” (zero não resultante de arredondamento) e “(0)” viram 0; “...” (não aplicável) e “NE” (não estimado) viram <code>NaN</code>, sem imputação, porque nenhum método de preenchimento seria defensável para dados de inventário.</li>
  <li><b>Normalização:</b> remoção de notas de rodapé nos rótulos e correção de grafias (“Ferrroviário”, “Ceu”).</li>
  <li><b>Valores negativos mantidos:</b> reflorestamento e arborização urbana removem carbono e entram com sinal negativo.</li>
  <li><b>Validação:</b> a soma dos cinco setores reproduz o TOTAL publicado (diferença máxima de 0,00 t) e as partes por escopo e por gás somam o total de cada linha. Os arquivos brutos nunca são alterados e o log de decisões fica em <code>data/processed/etl_log.txt</code>.</li>
  <li><b>Métricas derivadas:</b> participação percentual, variação percentual, taxa de crescimento anual composta (CAGR) e coeficiente de variação (CV = desvio-padrão/média).</li>
</ul>
<p>Trechos centrais do pipeline (<code>src/etl.py</code>):</p>
<div class="code reveal"><pre><code>{code['parse']}</code></pre></div>
<div class="code reveal"><pre><code>{code['num']}</code></pre></div>
<div class="code reveal"><pre><code>{code['valid']}</code></pre></div>
</section>

<section id="resultados">
<h2>3. Resultados e discussão</h2>
<h3>3.1 RQ1 — Trajetória do total e composição setorial</h3>
<p>As emissões totais caíram de {fmt_mt(m['total_2012'])} Mt CO₂e em 2012 para {fmt_mt(m['total_2024'])} Mt em 2024 ({m['var_2012_2024_pct']:.1f}%; CAGR de {m['cagr_total_pct']:.2f}% ao ano). A série subiu até o pico de {fmt_mt(m['pico_valor'])} Mt em {m['pico_ano']}, e o nível de 2024 está {abs(m['var_2014_2024_pct']):.1f}% abaixo desse pico. Entre 2019 e 2020 houve queda de {abs(m['var_2019_2020_pct']):.1f}% (mínimo de {fmt_mt(m['min_valor'])} Mt) e, em 2021, recuperação de {m['var_2020_2021_pct']:.1f}%. Uma regressão linear simples indica tendência de {fmt_mt(m['tendencia_t_por_ano'])} Mt por ano (R² = {m['tendencia_r2']:.2f}, p = {m['tendencia_p']:.3f}); com apenas 13 observações autocorrelacionadas, vale como descrição da inclinação, não como inferência causal.</p>
<figure class="reveal">
  <div class="ctrl"><div class="seg" data-for="g1"><button class="on" data-m="abs">Valores absolutos</button><button data-m="pct">Participação (%)</button></div><span class="note">Clique na legenda para ocultar setores.</span></div>
  <div id="g1" class="plot" role="img" aria-label="Barras empilhadas das emissões por setor de 2012 a 2024"></div>
  <noscript><img src="assets/fig1_total_setores.png" alt="Emissões por setor, 2012–2024"></noscript>
  <figcaption><b>Figura 1.</b> Emissões por setor, 2012–2024 (interativo). Fonte: Data.Rio/IPP, Tabela 3696; elaboração própria.</figcaption>
</figure>
<p>A composição mudou: energia estacionária subiu de {pp['2012']['Energia Estacionária']:.1f}% para {pp['2024']['Energia Estacionária']:.1f}% do total, enquanto transportes recuaram de {pp['2012']['Transportes']:.1f}% para {pp['2024']['Transportes']:.1f}%. Esse movimento não indica crescimento da energia estacionária, que variou apenas {m['var_setor_2012_2024_pct']['Energia Estacionária']:+.1f}% no período. Ele resulta da queda de {abs(m['var_setor_2012_2024_pct']['Transportes']):.1f}% em transportes, que reduziu o denominador. Resíduos cresceram {m['var_setor_2012_2024_pct']['Resíduos']:.1f}% e processos industriais caíram {abs(m['var_setor_2012_2024_pct']['Processos Industriais e Uso de Produtos']):.1f}%. O setor agropecuário, florestal e de uso do solo dobrou, mas parte de uma base mínima (cerca de 0,1% a 0,2% do total).</p>
<div class="tw reveal"><table>
<thead><tr><th>Setor</th><th>2012</th><th>2019</th><th>2024</th><th>Var. 2012–24</th><th>CV 2012–24</th></tr></thead>
<tbody>
{tabela_resumo(m)}
</tbody></table></div>
<p class="note">Tabela 1. Participação no total, variação e coeficiente de variação por setor (clique no cabeçalho para ordenar).</p>
<figure class="reveal">
  <div class="ctrl"><label>Comparar <select id="sa"></select></label><label>com <select id="sb"></select></label></div>
  <div id="gs" class="plot" role="img" aria-label="Barras horizontais com a participação de cada setor em dois anos escolhidos"></div>
  <noscript><img src="assets/fig2_participacao.png" alt="Participação setorial em 2012, 2019 e 2024"></noscript>
  <figcaption><b>Figura 2.</b> Composição setorial em dois anos à escolha (padrão: 2012 e 2024).</figcaption>
</figure>
<p>Entre os dois maiores setores, transportes são o mais sensível a choques (CV de {m['cv_setor_pct']['Transportes']:.1f}%, contra {m['cv_setor_pct']['Energia Estacionária']:.1f}% da energia estacionária). A queda de 2020 é compatível com as restrições de mobilidade da pandemia de covid-19, e a recuperação posterior é parcial, o que as séries de aviação e transporte rodoviário (RQ3) detalham. Associar a queda à pandemia é uma interpretação de contexto; os dados do inventário não medem a causa.</p>
<div class="take reveal"><b class="t">Em síntese · RQ1</b>O total caiu {abs(m['var_2012_2024_pct']):.1f}% em 12 anos, com um vale em {m['min_ano']}. A fatia da energia estacionária cresceu por efeito de denominador, e não por aumento absoluto.</div>

<h3>3.2 RQ2 — Volatilidade por escopo</h3>
<p>O Escopo 1 (emissões dentro do território) responde por entre {esc['2014']['Escopo 1']:.0f}% (2014) e {esc['2022']['Escopo 1']:.0f}% (2022) do total e é o componente mais estável (CV de {m['cv_escopo_pct']['Escopo 1']:.1f}%). O Escopo 3 oscila mais (CV de {m['cv_escopo_pct']['Escopo 3']:.1f}%) e cai de cerca de {esc['2014']['Escopo 3']:.0f}% do total em 2014 para {esc['2021']['Escopo 3']:.0f}% em 2021. O Escopo 2, ligado à eletricidade consumida, tem CV de {m['cv_escopo_pct']['Escopo 2']:.1f}%: atinge {fmt_mt(m['escopo2_max'][1])} Mt em {m['escopo2_max'][0]} ({esc['2014']['Escopo 2']:.1f}% do total) e apenas {fmt_mt(m['escopo2_min'][1])} Mt em {m['escopo2_min'][0]}.</p>
<figure class="reveal">
  <div class="ctrl"><div class="seg" data-for="g2"><button class="on" data-m="abs">Milhões de t</button><button data-m="share">% do total</button><button data-m="idx">Índice 2012 = 100</button></div></div>
  <div id="g2" class="plot" role="img" aria-label="Linhas das emissões por escopo de 2012 a 2024"></div>
  <noscript><img src="assets/fig3_escopos.png" alt="Emissões por escopo"></noscript>
  <figcaption><b>Figura 3.</b> Emissões por escopo, 2012–2024 (interativo). O índice mostra a oscilação relativa de cada escopo em relação a 2012.</figcaption>
</figure>
<p>Como o Escopo 2 depende do fator de emissão da rede elétrica, e não só do consumo da cidade, grande parte da sua oscilação deve refletir a matriz do sistema nacional naquele ano. Um indício nos próprios dados é a associação entre o Escopo 2 e a geração de energia elétrica para o Sistema Interligado Nacional (SIN) reportada como item informativo, com r = {m['corr_escopo2_sin']:.2f} (Figura 4). A correlação é moderada, e a relação não é linear nem estável no tempo (por exemplo, 2021 destoa). Portanto, o resultado sugere, sem comprovar, que o Escopo 2 é um indicador ruim de esforço local de eficiência e que metas urbanas devem distinguir reduções sob controle da cidade (Escopo 1) das induzidas pela rede.</p>
<figure class="reveal">
  <div id="g3" class="plot" role="img" aria-label="Dispersão entre Escopo 2 e geração para o SIN, um ponto por ano"></div>
  <figcaption><b>Figura 4.</b> Escopo 2 contra a geração para o SIN no território; cada ponto é um ano (passe o mouse para ver o ano).</figcaption>
</figure>
<div class="take reveal"><b class="t">Em síntese · RQ2</b>O Escopo 1 é estável e o Escopo 2 é o mais volátil ({m['cv_escopo_pct']['Escopo 2']:.0f}% de CV). Por depender da rede elétrica, ele é um indicador frágil do esforço local.</div>

<h3>3.3 RQ3 — Subsetores e gases por trás da redução líquida</h3>
<p>A redução líquida de {fmt_mt(abs(m['delta_total']))} Mt entre 2012 e 2024 é a soma de movimentos de sinais opostos. Os três maiores contribuintes de queda são aviação (−1,21 Mt; −37,9%), transporte rodoviário (−0,92 Mt; −17,1%) e produção de ferro e aço (−0,66 Mt; −28,8%), que juntos somam {fmt_mt(abs(m['soma_deltas_top3_queda']))} Mt, ou seja, mais que toda a redução líquida. O aterramento de resíduos (+0,38 Mt; +24,0%), as indústrias de energia (+0,19 Mt) e as indústrias de manufatura e construção (+0,16 Mt) compensam parte da queda. Na aviação, a queda já está presente antes da pandemia (de 3,20 Mt em 2012 para 2,29 Mt em 2019), logo não se explica apenas por 2020.</p>
<figure class="reveal">
  <div class="ctrl"><label>De <select id="y0"></select></label><label>até <select id="y1"></select></label><span class="note">Os 8 maiores recuos e aumentos entre os anos escolhidos.</span></div>
  <div id="g6" class="plot" role="img" aria-label="Barras horizontais com a variação absoluta por subsetor entre dois anos escolhidos"></div>
  <figcaption><b>Figura 5.</b> Explorador de variações por subsetor (interativo; padrão 2012→2024). Verde indica redução e laranja, aumento.</figcaption>
</figure>
<p>Quanto aos gases, o CO₂ permanece dominante, mas perde participação: de {gas['2012']['CO2']:.1f}% (2012) para {gas['2024']['CO2']:.1f}% (2024), com queda absoluta de {abs(m['var_gas_2012_2024_pct']['CO2']):.1f}%. O metano cresce {m['var_gas_2012_2024_pct']['CH4']:.1f}% e sua participação sobe de {gas['2012']['CH4']:.1f}% para {gas['2024']['CH4']:.1f}%, em linha com o aumento do aterramento de resíduos, fonte típica de CH₄. O N₂O fica praticamente estável em termos absolutos ({m['var_gas_2012_2024_pct']['N2O']:+.1f}%) e responde por menos de 2% do total. Assim, a descarbonização observada é essencialmente de CO₂ (combustíveis), e a agenda de resíduos e metano ganha peso relativo.</p>
<figure class="reveal">
  <div class="pair"><div id="g4" class="plot" role="img" aria-label="Emissões por gás, áreas empilhadas"></div><div id="g5" class="plot" role="img" aria-label="Participação de CH4 e N2O ao longo do tempo"></div></div>
  <noscript><img src="assets/fig4_gases.png" alt="Emissões por gás e participação de CH4 e N2O"></noscript>
  <figcaption><b>Figura 6.</b> Emissões por gás (esquerda) e participação de CH₄ e N₂O no total (direita).</figcaption>
</figure>
<div class="take reveal"><b class="t">Em síntese · RQ3</b>Aviação, rodoviário e siderurgia explicam a queda; o aterramento a atenua. O metano passa de {gas['2012']['CH4']:.1f}% para {gas['2024']['CH4']:.1f}% das emissões.</div>
</section>

<section id="conclusao">
<h2>4. Conclusão</h2>
<p><b>RQ1.</b> As emissões do Rio caíram {abs(m['var_2012_2024_pct']):.1f}% entre 2012 e 2024, com pico em {m['pico_ano']} e mínimo em {m['min_ano']}; energia estacionária e transportes concentram cerca de {en_tr:.0f}% do total. <b>RQ2.</b> O Escopo 2 é o mais volátil e se associa à geração do sistema elétrico nacional, o que o torna um indicador frágil do esforço local. <b>RQ3.</b> A redução líquida vem de aviação, transporte rodoviário e siderurgia, e o metano ganha participação por causa dos resíduos.</p>
<p><b>Limitações.</b> (i) São 13 pontos anuais, o que limita testes estatísticos; (ii) a série foi revisada em 2024 e pode ser revisada de novo; (iii) o inventário não traz causas, de modo que explicações como a pandemia ou a matriz elétrica são hipóteses de contexto; (iv) valores “NE” e “...” não foram imputados; (v) a análise é agregada para a cidade e não diferencia bairros ou fontes individuais.</p>
<p><b>Trabalhos futuros.</b> Cruzar a série com população, PIB municipal e fator de emissão da rede para calcular intensidades per capita e por unidade de PIB; decompor a variação do Escopo 2 em efeito consumo e efeito fator de emissão; e comparar o Rio com outras cidades signatárias do GPC.</p>
</section>

<section id="fair">
<h2>5. Disponibilidade dos dados e declaração FAIR</h2>
<ul>
  <li><b>Findable:</b> repositório com <code>README.md</code>, palavras-chave, autoria, disciplina e semestre; dados brutos referenciados pelo <a href="{c['dados_url']}">link da fonte</a>.</li>
  <li><b>Accessible:</b> repositório público no GitHub; scripts rodam sem credenciais; artigo servido pelo GitHub Pages, com layout responsivo.</li>
  <li><b>Interoperable:</b> dados processados em <code>.csv.gz</code> (formato aberto) e <code>data/data_dictionary.md</code> descrevendo cada variável.</li>
  <li><b>Reusable:</b> licença MIT (código) e CC BY 4.0 (dados e texto); <code>requirements.txt</code> com versões fixas.</li>
</ul>
<p>Para reproduzir todo o pipeline:</p>
<div class="code reveal"><pre><code>git clone {c['repo_url']}.git
cd {c['repo_url'].rsplit('/', 1)[-1]}
python -m venv .venv &amp;&amp; source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python -m src.etl          # data/raw/3696.xls -&gt; data/processed/*.csv.gz
python -m src.analysis     # figuras e métricas em docs/assets/
python -m src.build_site   # regenera docs/index.html</code></pre></div>
</section>

<section id="refs">
<h2>6. Referências</h2>
<ol class="refs">
<li>HUNTER, J. D. Matplotlib: a 2D graphics environment. <i>Computing in Science &amp; Engineering</i>, v. 9, n. 3, p. 90–95, 2007.</li>
<li>INTERGOVERNMENTAL PANEL ON CLIMATE CHANGE (IPCC). <i>Climate Change 2014: Synthesis Report</i>. Genebra: IPCC, 2014.</li>
<li>McKINNEY, W. Data structures for statistical computing in Python. In: PYTHON IN SCIENCE CONFERENCE, 9., 2010. <i>Proceedings…</i>, p. 56–61, 2010.</li>
<li>PLOTLY TECHNOLOGIES INC. <i>Collaborative data science</i>. Montreal: Plotly Technologies Inc., 2015. Disponível em: https://plot.ly.</li>
<li>RIO DE JANEIRO (Município). Instituto Municipal de Urbanismo Pereira Passos (IPP). <i>Emissões de gases de efeito estufa (GEE) da Cidade do Rio de Janeiro, em t CO₂e — 2012 a 2024</i> (Tabela 3696). Data.Rio, set. 2026. Disponível em: <a href="{c['dados_url']}">{c['dados_url']}</a>. Acesso em: 13 nov. 2026.</li>
<li>WILKINSON, M. D. et al. The FAIR Guiding Principles for scientific data management and stewardship. <i>Scientific Data</i>, v. 3, art. 160018, 2016.</li>
<li>WORLD RESOURCES INSTITUTE (WRI); C40 CITIES CLIMATE LEADERSHIP GROUP; ICLEI. <i>Global Protocol for Community-Scale Greenhouse Gas Emission Inventories (GPC)</i>: an accounting and reporting standard for cities. Washington, DC: WRI, 2014.</li>
</ol>
</section>
</main>

<footer>
  {html.escape(c['disciplina'])} · {html.escape(c['instituicao'])} · {html.escape(c['semestre'])}.<br>
  Texto e dados processados sob licença <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>; código sob licença MIT. Dados originais: Data.Rio/IPP.
</footer>
</div>
<button id="up" aria-label="Voltar ao topo">↑</button>
<script>
{JS.replace('__DATA__', json.dumps(dados, ensure_ascii=False))}
</script>
<noscript><p class="note" style="text-align:center">Os gráficos interativos exigem JavaScript; versões estáticas estão incluídas.</p></noscript>
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
