"""Step 5: build a single self-contained HTML dashboard (output/dashboard.html).
Open it in any browser, or upload it as a shared page for your boss. No internet needed to view."""
import json
from config import OUT

TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Investor Profiler</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1b2430;--muted:#6b7585;--line:#e2e6ec;--accent:#1f5fbf;--good:#1a7f4b;--bad:#b42318}
@media (prefers-color-scheme:dark){:root{--bg:#0f1420;--card:#171e2d;--ink:#e8edf5;--muted:#9aa5b5;--line:#263146;--accent:#6ea8ff;--good:#4cd08a;--bad:#ff8a80}}
*{box-sizing:border-box}body{margin:0;font:14px/1.45 system-ui,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--ink)}
header{padding:16px 20px;border-bottom:1px solid var(--line);background:var(--card);display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between}
h1{font-size:18px;margin:0}h2{font-size:15px;margin:0 0 8px}h3{font-size:13px;margin:12px 0 6px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
nav button{background:none;border:0;padding:8px 12px;cursor:pointer;color:var(--muted);border-bottom:2px solid transparent;font:inherit}
nav button.on{color:var(--accent);border-color:var(--accent);font-weight:600}
main{padding:16px 20px;max-width:1280px;margin:auto}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}
.kpi b{display:block;font-size:20px;margin-top:4px}.kpi span{color:var(--muted);font-size:12px}
table{width:100%;border-collapse:collapse}th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
th{font-size:12px;color:var(--muted);font-weight:600;cursor:pointer;user-select:none}
tr.click{cursor:pointer}tr.click:hover td{background:rgba(31,95,191,.08)}
td.num,th.num{text-align:right}.pos{color:var(--good)}.neg{color:var(--bad)}
.tag{display:inline-block;padding:2px 8px;border-radius:999px;background:rgba(31,95,191,.12);color:var(--accent);font-size:12px;margin:2px 4px 2px 0}
.bar{height:8px;background:var(--line);border-radius:4px;overflow:hidden;min-width:120px}.bar i{display:block;height:100%;background:var(--accent)}
input,select{font:inherit;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);min-width:220px}
.muted{color:var(--muted)}.small{font-size:12px}.wrap{overflow-x:auto}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.45);display:none;align-items:flex-start;justify-content:center;padding:30px 12px;overflow:auto}
.modal.on{display:flex}.modal .box{background:var(--card);border-radius:12px;max-width:1000px;width:100%;padding:18px;border:1px solid var(--line)}
.close{float:right;cursor:pointer;background:none;border:0;color:var(--ink);font-size:20px}
.note{font-size:12px;color:var(--muted);border-left:3px solid var(--line);padding-left:10px;margin:8px 0}
</style></head><body>
<header><div><h1>Investor Profiler</h1><div class="muted small" id="asof"></div></div>
<nav><button data-tab="stock" class="on">Company view</button><button data-tab="types">Investor types</button><button data-tab="investor">Find an investor</button><button data-tab="method">Method</button></nav></header>
<main>
<section id="tab-stock">
  <div class="card"><div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center"><label>Company <select id="sym"></select></label><span class="muted small" id="symInfo"></span></div></div>
  <div class="grid" id="stockKpis"></div>
  <div class="card"><h2>Shareholding (latest quarter)</h2><div class="wrap" id="holdTbl"></div></div>
  <div class="card"><h2>Who bought, by investor type</h2><div class="wrap" id="typeBuyTbl"></div></div>
  <div class="card"><h2>Investors in this stock</h2><p class="note">Click any investor to see their full trade history, round trips and returns.</p><div class="wrap" id="invTbl"></div></div>
</section>
<section id="tab-types" hidden>
  <div class="card"><h2>What each investor type has in common</h2><p class="note">Medians across all investors of that type in the deal data. Click a row to see its investors.</p><div class="wrap" id="typesTbl"></div></div>
</section>
<section id="tab-investor" hidden>
  <div class="card"><input id="q" placeholder="Type an investor name..."> <span class="muted small" id="qCount"></span><div class="wrap" id="allTbl" style="margin-top:10px"></div></div>
</section>
<section id="tab-method" hidden>
  <div class="card"><h2>How the numbers are built</h2><div id="method"></div></div>
</section>
</main>
<div class="modal" id="modal"><div class="box"><button class="close" onclick="closeM()">×</button><div id="mBody"></div></div></div>
<script>
const DATA = /*DATA*/;
const $ = s => document.querySelector(s);
const fmtN = (v,d=0)=> v==null||isNaN(v)?'–':Number(v).toLocaleString('en-IN',{maximumFractionDigits:d,minimumFractionDigits:d});
const fmtCr = v => v==null?'–':'₹'+ (v/1e7).toLocaleString('en-IN',{maximumFractionDigits:2})+' Cr';
const fmtP = (v,signed=true)=> v==null?'–':(signed&&v>0?'+':'')+(v*100).toFixed(1)+'%';
const cls = v => v==null?'':(v>=0?'pos':'neg');
const esc = s => String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const clientByName = Object.fromEntries(DATA.clients.map(c=>[c.name,c]));

function table(headers, rows, opts={}){ // rows: array of {cells:[html], click: fn}
  const id = 't'+Math.random().toString(36).slice(2,8);
  const th = headers.map((h,i)=>`<th class="${h.num?'num':''}">${esc(h.label??h)}</th>`).join('');
  const body = rows.map((r,ri)=>`<tr class="${r.click?'click':''}" data-r="${ri}">`+r.cells.map((c,i)=>`<td class="${headers[i]&&headers[i].num?'num':''}">${c}</td>`).join('')+'</tr>').join('');
  return `<table id="${id}"><thead><tr>${th}</tr></thead><tbody>${body||'<tr><td class="muted">No rows</td></tr>'}</tbody></table>`;
}
function bindRows(container, rows){
  container.querySelectorAll('tr.click').forEach(tr=>tr.onclick=()=>rows[+tr.dataset.r].click());
}

// ---- Company view
function renderStock(){
  const sym = $('#sym').value;
  const co = DATA.companies.find(c=>c.symbol===sym);
  if(!co){$('#stockKpis').innerHTML='';return;}
  const invs = DATA.clients.filter(c=>c.trades.some(t=>t.symbol===sym));
  const invested = invs.reduce((s,c)=>s+c.positions.filter(p=>p.symbol===sym).reduce((a,p)=>a+p.invested,0),0);
  const curVal = invs.reduce((s,c)=>s+c.positions.filter(p=>p.symbol===sym).reduce((a,p)=>a+p.current_value,0),0);
  const buyVal = Object.values(co.buy_value_by_type).reduce((a,b)=>a+b,0);
  $('#symInfo').textContent = `Last close ₹${fmtN(co.last_price,2)} · ${co.deal_count} bulk/block deals · as of ${DATA.as_of}`;
  $('#stockKpis').innerHTML = [
    ['Investors seen in deals', fmtN(invs.length)],
    ['Buy value in deals', fmtCr(buyVal)],
    ['Open positions (cost)', fmtCr(invested)],
    ['Open positions (value today)', fmtCr(curVal)],
  ].map(([a,b])=>`<div class="kpi"><span>${a}</span><b>${b}</b></div>`).join('');

  const hs = DATA.holdings.filter(h=>h.Symbol===sym);
  const latestQ = hs.length? hs.map(h=>h.Quarter).sort().pop() : null;
  const hRows = hs.filter(h=>h.Quarter===latestQ).sort((a,b)=>(b.Pct||0)-(a.Pct||0)).map(h=>({cells:[
    esc(h.Category), `<span class="small">${fmtN(h.Shares)}</span>`, fmtN(h.Pct,2)+'%',
    `<div class="bar"><i style="width:${Math.min(100,h.Pct||0)}%"></i></div>`]}));
  $('#holdTbl').innerHTML = hs.length ? `<div class="muted small">Quarter: ${esc(latestQ)}</div>`+table(['Category',{label:'Shares',num:1},{label:'% held',num:1},''],hRows)
     : '<p class="muted">No shareholding-pattern files loaded for this company yet. Add them to data/shareholding and re-run.</p>';

  const tb = Object.entries(co.buy_value_by_type).sort((a,b)=>b[1]-a[1]).map(([t,v])=>({cells:[esc(t), fmtCr(v), fmtP(v/(buyVal||1),false)]}));
  $('#typeBuyTbl').innerHTML = table(['Investor type',{label:'Buy value',num:1},{label:'Share of buys',num:1}], tb);

  const rows = invs.map(c=>{
    const pos = c.positions.filter(p=>p.symbol===sym);
    const inv = pos.reduce((a,p)=>a+p.invested,0), cv = pos.reduce((a,p)=>a+p.current_value,0);
    const qty = pos.reduce((a,p)=>a+p.qty,0);
    const cg = pos.length? (pos.reduce((a,p)=>a+(p.cagr??0),0)/pos.length) : null;
    const days = c.summary.avg_holding_days;
    return {click:()=>openClient(c.name), cells:[
      esc(c.name), `<span class="small">${esc(c.type)}</span>`, fmtN(qty), fmtCr(inv), fmtCr(cv),
      `<span class="${cls(cg)}">${fmtP(cg)}</span>`, days==null?'–':fmtN(days)+' d',
      esc(c.summary.buy_style||'–')]};
  }).sort((a,b)=>0);
  const tbl = table(['Investor',{label:'Type'},{label:'Held shares',num:1},{label:'Cost',num:1},{label:'Value today',num:1},{label:'CAGR (open)',num:1},{label:'Avg hold',num:1},{label:'Buy style'}], rows);
  $('#invTbl').innerHTML = tbl; bindRows($('#invTbl'), rows);
}

// ---- Investor types
function renderTypes(){
  const rows = DATA.types.map(t=>({click:()=>{ $('#q').value=''; setTab('investor'); }, cells:[
     `<b>${esc(t.type)}</b>`, fmtN(t.clients), fmtCr(t.buy_value), fmtCr(t.current_value),
     t.median_holding_days==null?'–':fmtN(t.median_holding_days)+' d',
     `<span class="${cls(t.median_cagr)}">${fmtP(t.median_cagr)}</span>`,
     t.pct_dip_buyers==null?'–':fmtP(t.pct_dip_buyers,false),
     (t.top_stocks||[]).map(s=>`<span class="tag">${esc(s)}</span>`).join('')]}));
  $('#typesTbl').innerHTML = table(['Investor type',{label:'Investors',num:1},{label:'Buy value',num:1},{label:'Value today',num:1},{label:'Median hold',num:1},{label:'Median CAGR',num:1},{label:'% buys dips',num:1},{label:'Top stocks'}], rows);
  bindRows($('#typesTbl'), rows);
}

// ---- Find investor
function renderAll(){
  const q = $('#q').value.trim().toLowerCase();
  const list = DATA.clients.filter(c=>!q || c.name.toLowerCase().includes(q)).slice(0,300);
  $('#qCount').textContent = `${list.length} shown of ${DATA.clients.length} investors`;
  const rows = list.map(c=>({click:()=>openClient(c.name), cells:[
     esc(c.name), `<span class="small">${esc(c.type)}</span>`, fmtN(c.summary.stocks),
     fmtCr(c.summary.buy_value), fmtCr(c.summary.current_value),
     `<span class="${cls(c.summary.median_cagr)}">${fmtP(c.summary.median_cagr)}</span>`,
     c.summary.avg_holding_days==null?'–':fmtN(c.summary.avg_holding_days)+' d',
     `${esc(c.summary.horizon||'–')}`, esc(c.summary.buy_style||'–')]}));
  $('#allTbl').innerHTML = table(['Investor',{label:'Type'},{label:'Stocks',num:1},{label:'Bought',num:1},{label:'Value today',num:1},{label:'Median CAGR',num:1},{label:'Avg hold',num:1},{label:'Horizon'},{label:'Buy style'}], rows);
  bindRows($('#allTbl'), rows);
}

// ---- Investor detail
function openClient(name){
  const c = clientByName[name]; if(!c) return;
  const s = c.summary;
  const tags = [c.type, s.horizon, s.buy_style, s.concentration].filter(Boolean).map(t=>`<span class="tag">${esc(t)}</span>`).join('');
  const pos = table(['Stock',{label:'Qty',num:1},{label:'Avg cost',num:1},{label:'Price today',num:1},{label:'Invested',num:1},{label:'Value today',num:1},{label:'Return',num:1},{label:'CAGR',num:1},{label:'Since',num:0},{label:'Days',num:1}],
     c.positions.map(p=>({cells:[esc(p.symbol),fmtN(p.qty),fmtN(p.avg_cost,2),fmtN(p.current_price,2),fmtCr(p.invested),fmtCr(p.current_value),
       `<span class="${cls(p.unrealised_pct)}">${fmtP(p.unrealised_pct)}</span>`,`<span class="${cls(p.cagr)}">${fmtP(p.cagr)}</span>`,esc(p.first_buy),fmtN(p.days_held)]})));
  const rt = table(['Stock',{label:'Bought'},{label:'Sold'},{label:'Qty',num:1},{label:'Buy ₹',num:1},{label:'Sell ₹',num:1},{label:'Days',num:1},{label:'CAGR',num:1}],
     c.round_trips.map(r=>({cells:[esc(r.symbol),esc(r.buy_date),esc(r.sell_date),fmtN(r.qty),fmtN(r.buy_price,2),fmtN(r.sell_price,2),fmtN(r.days),`<span class="${cls(r.cagr)}">${fmtP(r.cagr)}</span>`]})));
  const tr = table(['Date',{label:'Stock'},{label:'Side'},{label:'Qty',num:1},{label:'Price',num:1},{label:'Value',num:1},{label:'Deal'},{label:'Buy style'}],
     c.trades.slice().sort((a,b)=>b.date.localeCompare(a.date)).map(t=>({cells:[esc(t.date),esc(t.symbol),`<span class="${t.side==='BUY'?'pos':'neg'}">${t.side}</span>`,fmtN(t.qty),fmtN(t.price,2),fmtCr(t.value),esc(t.kind),esc(t.style||'–')]})));
  $('#mBody').innerHTML = `<h2>${esc(c.name)}</h2><div>${tags}</div>
    <div class="grid" style="margin:12px 0"><div class="kpi"><span>Bought (gross)</span><b>${fmtCr(s.buy_value)}</b></div><div class="kpi"><span>Value today</span><b>${fmtCr(s.current_value)}</b></div>
    <div class="kpi"><span>Avg holding</span><b>${s.avg_holding_days==null?'–':fmtN(s.avg_holding_days)+' days'}</b></div><div class="kpi"><span>Median CAGR</span><b class="${cls(s.median_cagr)}">${fmtP(s.median_cagr)}</b></div></div>
    <h3>Open positions</h3><div class="wrap">${pos}</div><h3>Round trips (closed)</h3><div class="wrap">${rt}</div><h3>All deals</h3><div class="wrap">${tr}</div>`;
  $('#modal').classList.add('on');
}
function closeM(){ $('#modal').classList.remove('on'); }
$('#modal').onclick = e => { if(e.target.id==='modal') closeM(); };

function setTab(t){
  document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('on', b.dataset.tab===t));
  ['stock','types','investor','method'].forEach(x=>$('#tab-'+x).hidden = x!==t);
}
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>setTab(b.dataset.tab));
$('#q').oninput = renderAll;
$('#sym').onchange = renderStock;

$('#asof').textContent = `Data as of ${DATA.as_of} · ${DATA.companies.length} companies · ${DATA.clients.length} investors`;
$('#sym').innerHTML = DATA.companies.map(c=>`<option value="${esc(c.symbol)}">${esc(c.symbol)}</option>`).join('');
$('#method').innerHTML = `
<p><b>Source data.</b> Bulk and block deals from NSE (named buyers and sellers with date, quantity and price), shareholding patterns filed quarterly (category totals), and daily closing prices.</p>
<p><b>Cost and value.</b> Cost is the quantity-weighted average buy price of shares still held. Value today is quantity times the latest close.</p>
<p><b>CAGR.</b> (exit price ÷ entry price) ^ (365 ÷ days held) − 1. Only shown for holdings of at least 30 days.</p>
<p><b>Holding period.</b> Round trips are matched first-in, first-out. Average holding is weighted by quantity. Open positions use days since the first buy.</p>
<p><b>Buy style.</b> Price on the day of the buy vs the 52-week high: below 85% = buys dips, above 97% = buys strength, otherwise mid-range. This is an inference from trading behaviour, not a disclosed strategy.</p>
<p><b>Investor type.</b> Rule-based from the investor's name. Override any name in data/client_types_override.csv.</p>
<p class="note"><b>Limits.</b> Bulk and block deals show only large trades. Smaller trades are not visible. Mutual fund and FPI holdings are only partly visible from deals, so a full fund-level view needs their monthly portfolio disclosures. Investing style and horizon are estimates.</p>`;

renderStock(); renderTypes(); renderAll();
</script></body></html>"""


def main():
    data = json.loads((OUT / "data.json").read_text(encoding="utf-8"))
    html = TEMPLATE.replace("/*DATA*/", json.dumps(data, default=str))
    (OUT / "dashboard.html").write_text(html, encoding="utf-8")
    print(f"Wrote {OUT / 'dashboard.html'}")


if __name__ == "__main__":
    main()
