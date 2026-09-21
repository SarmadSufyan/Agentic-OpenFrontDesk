"""A minimal, professional dashboard served by the API at /app.

Deliberately simple (single file, vanilla JS, no build step) per the project's "keep the frontend
simple for now, swap for Next.js later" decision. Talks to the JSON API on the same origin using the
JWT from login. See docs/01-product-ux.md.
"""

from __future__ import annotations

DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OpenFrontDesk — Dashboard</title>
<style>
  :root{--bg:#f4f7f7;--surface:#fff;--surface-2:#eaf0ef;--ink:#16242a;--muted:#5b6d71;--line:#d8e2e1;
        --accent:#0f9488;--accent-ink:#0a5f57;--accent-soft:#d8efeb;--green:#2f9e59;--amber:#b5731a;--radius:12px;}
  @media(prefers-color-scheme:dark){:root{--bg:#0d1618;--surface:#152121;--surface-2:#1a2828;--ink:#e9efef;
        --muted:#a0b2b3;--line:#273636;--accent:#34c9b8;--accent-ink:#8ee2d6;--accent-soft:#10302c;--green:#5fce8a;--amber:#e0a458;}}
  *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);
     font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.5;}
  a{color:var(--accent-ink)} .hidden{display:none!important}
  header{display:flex;align-items:center;gap:12px;padding:12px 18px;border-bottom:1px solid var(--line);
     background:var(--surface);position:sticky;top:0;flex-wrap:wrap;}
  header .brand{font-weight:700} header .ws{color:var(--muted);font-size:.9rem}
  header .sp{flex:1}
  button{font:inherit;cursor:pointer;border-radius:8px;border:1px solid var(--line);background:var(--surface);
     color:var(--ink);padding:8px 12px;}
  button.primary{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
  nav.tabs{display:flex;gap:6px;padding:10px 18px;flex-wrap:wrap;border-bottom:1px solid var(--line);background:var(--surface)}
  nav.tabs button{border-radius:999px;font-size:.9rem}
  nav.tabs button.active{background:var(--accent-soft);border-color:var(--accent);color:var(--accent-ink);font-weight:600}
  main{max-width:1000px;margin:0 auto;padding:20px 18px 60px}
  .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:16px}
  .kpi{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px}
  .kpi .n{font-size:1.9rem;font-weight:700} .kpi .l{color:var(--muted);font-size:.82rem}
  table{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--line);
     border-radius:var(--radius);overflow:hidden;font-size:.9rem}
  th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line)}
  th{background:var(--surface-2);font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
  tr:last-child td{border-bottom:none}
  .pill{font-size:.72rem;font-weight:600;padding:2px 9px;border-radius:999px;background:var(--surface-2)}
  .pill.booked,.pill.confirmed{background:var(--accent-soft);color:var(--accent-ink)}
  .card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:18px;margin-bottom:14px}
  label{display:block;font-size:.82rem;color:var(--muted);margin:10px 0 4px}
  input,textarea,select{width:100%;padding:9px 11px;border:1px solid var(--line);border-radius:8px;
     background:var(--bg);color:var(--ink);font:inherit}
  .row{display:flex;gap:12px;flex-wrap:wrap} .row>div{flex:1;min-width:160px}
  .muted{color:var(--muted)} .msg{padding:10px 12px;border-radius:8px;margin:10px 0;font-size:.9rem}
  .msg.err{background:#fdecec;color:#a12; border:1px solid #f2c0c0}
  .msg.ok{background:var(--accent-soft);color:var(--accent-ink)}
  /* login */
  #login{max-width:380px;margin:8vh auto;padding:26px;background:var(--surface);border:1px solid var(--line);border-radius:16px}
  #login h1{font-size:1.3rem;margin:0 0 4px} #login p{color:var(--muted);margin:0 0 16px;font-size:.9rem}
  h2{font-size:1.2rem;margin:.2em 0 .6em}
  .transcript{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px;max-height:320px;overflow:auto;font-size:.9rem}
  .line{margin:5px 0} .line b{text-transform:capitalize} .line.assistant b{color:var(--accent-ink)} .line.user b{color:var(--muted)}
</style>
</head>
<body>

<div id="login">
  <h1>🎙️ OpenFrontDesk</h1>
  <p>Sign in to your dashboard.</p>
  <div id="loginMsg"></div>
  <label>Email</label><input id="email" value="demo@openfrontdesk.local" autocomplete="username">
  <label>Password</label><input id="password" type="password" value="demodemo12" autocomplete="current-password">
  <div style="height:14px"></div>
  <button class="primary" style="width:100%" onclick="doLogin()">Sign in</button>
  <p class="muted" style="margin-top:14px">Demo login is pre-filled. Seed it with <code>scripts/seed_demo.py</code>.</p>
</div>

<div id="app" class="hidden">
  <header>
    <span class="brand">🎙️ OpenFrontDesk</span>
    <span class="ws" id="wsName"></span>
    <span class="sp"></span>
    <a href="/test" target="_blank"><button>📞 Test call</button></a>
    <button onclick="logout()">Log out</button>
  </header>
  <nav class="tabs" id="tabs"></nav>
  <main id="view"></main>
</div>

<script>
const $ = (id) => document.getElementById(id);
let TOKEN = null;
try { TOKEN = localStorage.getItem("ofd_token"); } catch(e){}

async function api(path, opts={}) {
  const headers = Object.assign({"Content-Type":"application/json"}, opts.headers||{});
  if (TOKEN) headers["Authorization"] = "Bearer " + TOKEN;
  const res = await fetch(path, Object.assign({}, opts, {headers}));
  if (res.status === 401) { logout(); throw new Error("Please sign in again."); }
  if (!res.ok) {
    let m = "Request failed ("+res.status+")";
    try { const j = await res.json(); m = (j.error&&j.error.message) || (j.detail&&(j.detail[0]?.msg||j.detail)) || m; } catch(e){}
    throw new Error(m);
  }
  if (res.status === 204) return null;
  return res.json();
}

async function doLogin() {
  $("loginMsg").innerHTML = "";
  try {
    const body = JSON.stringify({email:$("email").value, password:$("password").value});
    const t = await fetch("/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body});
    if (!t.ok) { const j = await t.json().catch(()=>({})); throw new Error((j.error&&j.error.message)||"Login failed"); }
    const data = await t.json();
    TOKEN = data.access_token;
    try { localStorage.setItem("ofd_token", TOKEN); } catch(e){}
    boot();
  } catch(err) { $("loginMsg").innerHTML = '<div class="msg err">'+err.message+'</div>'; }
}
function logout(){ TOKEN=null; try{localStorage.removeItem("ofd_token");}catch(e){}; $("app").classList.add("hidden"); $("login").classList.remove("hidden"); }

const TABS = [
  ["overview","Overview"],["calls","Calls"],["bookings","Bookings"],
  ["leads","Leads"],["knowledge","Knowledge"],["agent","Agent"],["audit","Audit"]
];
let active = "overview";
function renderTabs(){
  $("tabs").innerHTML = TABS.map(([k,l])=>`<button class="${k===active?'active':''}" onclick="go('${k}')">${l}</button>`).join("");
}
function go(k){ active=k; renderTabs(); render(); }

function esc(s){ return (s==null?"":String(s)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
function when(s){ return s ? new Date(s).toLocaleString() : "—"; }

async function render(){
  const v = $("view"); v.innerHTML = '<p class="muted">Loading…</p>';
  try {
    if (active==="overview"){
      const a = await api("/analytics/overview");
      const outcomes = Object.entries(a.calls_by_outcome||{}).map(([k,n])=>`${esc(k)}: ${n}`).join(" · ") || "—";
      v.innerHTML = `<h2>Overview</h2>
        <div class="kpis">
          <div class="kpi"><div class="n">${a.calls_total}</div><div class="l">Calls</div></div>
          <div class="kpi"><div class="n">${a.bookings_total}</div><div class="l">Bookings</div></div>
          <div class="kpi"><div class="n">${a.leads_total}</div><div class="l">Leads / messages</div></div>
          <div class="kpi"><div class="n">${a.minutes_total}</div><div class="l">Minutes handled</div></div>
        </div>
        <div class="card"><b>Call outcomes:</b> ${outcomes}</div>`;
    } else if (active==="calls"){
      const rows = await api("/calls");
      let html = `<h2>Calls</h2>`;
      if (!rows.length) { html += '<p class="muted">No calls yet.</p>'; }
      else {
        html += '<table><tr><th>When</th><th>Direction</th><th>Outcome</th><th>Caller</th><th>Secs</th><th></th></tr>';
        html += rows.map(r=>`<tr><td>${when(r.created_at)}</td><td>${esc(r.direction)}</td><td>${esc(r.outcome||'-')}</td><td>${esc(r.caller_number||'-')}</td><td>${r.duration_seconds}</td><td><button onclick="viewCall('${r.id}')">View</button></td></tr>`).join("");
        html += '</table>';
      }
      html += '<div id="callDetail" style="margin-top:14px"></div>';
      v.innerHTML = html;
    } else if (active==="audit"){
      const rows = await api("/audit");
      v.innerHTML = `<h2>Audit log</h2>` + table(rows, ["created_at","action","target"],
        ["When","Action","Target"], r=>({created_at:when(r.created_at)}));
    } else if (active==="bookings"){
      const rows = await api("/bookings");
      v.innerHTML = `<h2>Bookings</h2>` + table(rows, ["customer_name","service","start_at","status"],
        ["Customer","Service","When","Status"], r=>({start_at:when(r.start_at), status:pill(r.status)}));
    } else if (active==="leads"){
      const rows = await api("/leads");
      v.innerHTML = `<h2>Leads &amp; messages</h2>` + table(rows, ["name","phone","intent","message","created_at"],
        ["Name","Phone","Intent","Message","When"], r=>({created_at:when(r.created_at)}));
    } else if (active==="knowledge"){
      const docs = await api("/knowledge");
      v.innerHTML = `<h2>Knowledge base</h2>
        <div class="card"><b>Add text</b>
          <label>Title</label><input id="kt" placeholder="e.g. Pricing &amp; hours">
          <label>Content</label><textarea id="kc" rows="4" placeholder="Paste anything the agent should know…"></textarea>
          <div style="height:10px"></div><button class="primary" onclick="addKnowledge()">Add &amp; index</button>
          <div id="kMsg"></div>
        </div>` + table(docs, ["title","source_type","status","chunk_count"], ["Title","Type","Status","Chunks"], r=>({status:pill(r.status)}));
    } else if (active==="agent"){
      const ag = await api("/agents/current");
      v.innerHTML = `<h2>Agent settings</h2>
        <div class="card">
          <div class="row"><div><label>Name</label><input id="a_name" value="${esc(ag.name)}"></div>
            <div><label>Voice</label><input id="a_voice" value="${esc(ag.voice)}"></div>
            <div><label>Tone</label><input id="a_tone" value="${esc(ag.tone)}"></div></div>
          <label>Greeting</label><textarea id="a_greeting" rows="2">${esc(ag.greeting)}</textarea>
          <div style="height:12px"></div><button class="primary" onclick="saveAgent()">Save</button>
          <div id="aMsg"></div>
        </div>`;
    }
  } catch(err){ v.innerHTML = '<div class="msg err">'+esc(err.message)+'</div>'; }
}

function pill(s){ return `<span class="pill ${esc(s)}">${esc(s)}</span>`; }
function table(rows, keys, heads, tf){
  if(!rows || !rows.length) return '<p class="muted">Nothing here yet.</p>';
  const head = "<tr>"+heads.map(h=>`<th>${h}</th>`).join("")+"</tr>";
  const body = rows.map(r=>{ const t=tf?tf(r):{}; return "<tr>"+keys.map(k=>`<td>${k in t ? t[k] : esc(r[k])}</td>`).join("")+"</tr>"; }).join("");
  return `<table>${head}${body}</table>`;
}

async function addKnowledge(){
  $("kMsg").innerHTML="";
  try { await api("/knowledge/text",{method:"POST",body:JSON.stringify({title:$("kt").value||"Untitled", text:$("kc").value})});
    $("kMsg").innerHTML='<div class="msg ok">Added and indexed.</div>'; setTimeout(render,700);
  } catch(e){ $("kMsg").innerHTML='<div class="msg err">'+esc(e.message)+'</div>'; }
}
async function saveAgent(){
  $("aMsg").innerHTML="";
  try { await api("/agents/current",{method:"PUT",body:JSON.stringify({name:$("a_name").value,voice:$("a_voice").value,tone:$("a_tone").value,greeting:$("a_greeting").value})});
    $("aMsg").innerHTML='<div class="msg ok">Saved.</div>';
  } catch(e){ $("aMsg").innerHTML='<div class="msg err">'+esc(e.message)+'</div>'; }
}

async function viewCall(id){
  const d = $("callDetail"); d.innerHTML = '<p class="muted">Loading…</p>';
  try {
    const c = await api("/calls/" + id);
    const lines = (c.transcript||[]).map(t=>`<div class="line ${esc(t.role)}"><b>${esc(t.role)}:</b> ${esc(t.text)}</div>`).join("")
      || '<span class="muted">No transcript recorded.</span>';
    const lat = (c.latency_ms && c.latency_ms.llm_ttft && c.latency_ms.llm_ttft.p50_ms!=null)
      ? ` · LLM p50 ${c.latency_ms.llm_ttft.p50_ms}ms` : "";
    d.innerHTML = `<div class="card"><h3>Call detail</h3>
      <p class="muted">${when(c.started_at)} · ${esc(c.direction)} · outcome: ${esc(c.outcome||'-')} · ${c.duration_seconds}s${lat}</p>
      ${c.summary ? '<p><b>Summary:</b> '+esc(c.summary)+'</p>' : ''}
      <div class="transcript">${lines}</div></div>`;
  } catch(e){ d.innerHTML = '<div class="msg err">'+esc(e.message)+'</div>'; }
}

async function boot(){
  try {
    const me = await api("/auth/me");
    const ws = (me.memberships&&me.memberships[0]) ? me.memberships[0].tenant_name : "";
    $("wsName").textContent = ws ? ("· "+ws) : "";
    $("login").classList.add("hidden"); $("app").classList.remove("hidden");
    renderTabs(); render();
  } catch(e){ logout(); }
}
if (TOKEN) boot();
</script>
</body>
</html>
"""
