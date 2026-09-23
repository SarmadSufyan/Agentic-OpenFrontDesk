"""Public "custom solutions" contact page served at /contact.

Single file, vanilla JS, same visual language as the dashboard. Choices come from /contact/options so
the form and the API validation never drift apart. Replaced by the Next.js frontend in M5; the API
contract (POST /contact) stays the same.
"""

from __future__ import annotations

CONTACT_PAGE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Custom AI solutions - OpenFrontDesk</title>
<meta name="description" content="Tell us what you need: WhatsApp assistants, HR helpdesk bots, website chatbots, voice receptionists and workflow automations built around your business.">
<style>
  :root{--bg:#f6f8f8;--surface:#fff;--surface-2:#eef3f3;--ink:#132024;--muted:#5b6b6e;--line:#dde5e5;
        --accent:#0f8b7d;--accent-ink:#0b6f64;--accent-soft:#e3f4f1;--err:#a12;--radius:14px}
  @media (prefers-color-scheme: dark){:root{--bg:#0d1515;--surface:#141f1f;--surface-2:#1b2828;--ink:#e6efee;
        --muted:#a0b2b3;--line:#273636;--accent:#34c9b8;--accent-ink:#8ee2d6;--accent-soft:#10302c;--err:#f19999}}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.55}
  a{color:var(--accent-ink)}
  header{display:flex;align-items:center;gap:14px;padding:14px 22px;border-bottom:1px solid var(--line);background:var(--surface)}
  header .brand{font-weight:700;text-decoration:none;color:var(--ink)} header .sp{flex:1}
  header nav{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:4px 16px}
  header nav a{text-decoration:none;color:var(--muted);font-size:.93rem;white-space:nowrap}
  .wrap{max-width:1080px;margin:0 auto;padding:44px 22px 70px;display:grid;grid-template-columns:1fr 1.1fr;gap:44px}
  @media (max-width:860px){.wrap{grid-template-columns:1fr;gap:28px;padding-top:28px}}
  .eyebrow{color:var(--accent-ink);font-weight:600;font-size:.82rem;letter-spacing:.06em;text-transform:uppercase}
  h1{font-size:2.1rem;line-height:1.15;margin:.35em 0 .45em;letter-spacing:-.01em}
  .lead{color:var(--muted);font-size:1.05rem;margin:0 0 26px}
  .offer{display:grid;gap:12px;margin:0 0 28px;padding:0;list-style:none}
  .offer li{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:13px 15px}
  .offer b{display:block;font-size:.97rem} .offer span{color:var(--muted);font-size:.9rem}
  .steps{counter-reset:s;list-style:none;padding:0;margin:0;display:grid;gap:10px}
  .steps li{counter-increment:s;display:flex;gap:12px;align-items:flex-start;color:var(--muted);font-size:.94rem}
  .steps li::before{content:counter(s);flex:none;width:26px;height:26px;border-radius:50%;background:var(--accent-soft);
        color:var(--accent-ink);font-weight:700;display:flex;align-items:center;justify-content:center;font-size:.85rem}
  .steps b{color:var(--ink)}
  .card{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:26px}
  .card h2{margin:0 0 4px;font-size:1.25rem} .card .sub{color:var(--muted);margin:0 0 14px;font-size:.93rem}
  label{display:block;font-size:.84rem;color:var(--muted);margin:14px 0 5px;font-weight:500}
  label .req{color:var(--accent-ink)}
  input,select,textarea{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--bg);
        color:var(--ink);font:inherit}
  input:focus,select:focus,textarea:focus{outline:2px solid var(--accent);outline-offset:1px;border-color:transparent}
  .row{display:grid;grid-template-columns:1fr 1fr;gap:12px} @media (max-width:520px){.row{grid-template-columns:1fr}}
  .chips{display:flex;flex-wrap:wrap;gap:8px}
  .chip{position:relative}
  .chip input{position:absolute;opacity:0;pointer-events:none}
  .chip span{display:inline-block;padding:7px 12px;border:1px solid var(--line);border-radius:999px;font-size:.88rem;cursor:pointer;
        background:var(--bg);user-select:none}
  .chip input:checked + span{background:var(--accent-soft);border-color:var(--accent);color:var(--accent-ink);font-weight:600}
  .chip input:focus-visible + span{outline:2px solid var(--accent);outline-offset:2px}
  .hp{position:absolute;left:-10000px;width:1px;height:1px;overflow:hidden}
  button{font:inherit;cursor:pointer;border-radius:10px;border:1px solid var(--accent);background:var(--accent);color:#fff;
        font-weight:600;padding:12px 18px;width:100%;margin-top:20px}
  button[disabled]{opacity:.6;cursor:progress}
  .fine{color:var(--muted);font-size:.8rem;margin:12px 0 0}
  .msg{padding:11px 13px;border-radius:10px;margin:14px 0 0;font-size:.92rem}
  .msg.err{background:#fdecec;color:#a12;border:1px solid #f2c0c0}
  .done{text-align:left} .done h2{font-size:1.3rem}
  .btn{display:inline-block;margin-top:16px;padding:12px 18px;border-radius:10px;background:var(--accent);color:#fff;
        text-decoration:none;font-weight:600}
  .ghost{background:transparent;color:var(--accent-ink);border:1px solid var(--line);margin-left:8px}
  .hidden{display:none!important}
</style>
</head>
<body>
<header>
  <a class="brand" href="/">OpenFrontDesk</a>
  <span class="sp"></span>
  <nav><a href="/app">Dashboard</a><a href="/widget-demo">Chat widget</a><a href="/docs">API</a></nav>
</header>

<div class="wrap">
  <section>
    <div class="eyebrow">Custom solutions</div>
    <h1>AI assistants built around how your business actually works</h1>
    <p class="lead">OpenFrontDesk is free and open source. When you need more than the self-serve setup, tell us
      what you have in mind and we will personally set up a call to plan it with you.</p>
    <ul class="offer">
      <li><b>WhatsApp assistant</b><span>Answers customers on WhatsApp from your own knowledge base, books
        appointments and hands off to your team.</span></li>
      <li><b>HR and internal helpdesk</b><span>An assistant that answers staff questions from your policies,
        handbooks and onboarding documents.</span></li>
      <li><b>Website chatbot and voice receptionist</b><span>Trained on your services and prices, capturing
        leads around the clock.</span></li>
      <li><b>Workflow automation</b><span>Connect leads, calls and bookings to your CRM, sheets, email and
        chat tools with n8n, Zapier or Make, using your own accounts.</span></li>
    </ul>
    <ol class="steps">
      <li><div><b>Tell us what you need.</b> Two minutes, no commitment.</div></li>
      <li><div><b>We schedule a call.</b> You get a confirmation now and a personal reply within one
        business day.</div></li>
      <li><div><b>We build and hand over.</b> On your accounts and credentials, so you stay in control.</div></li>
    </ol>
  </section>

  <section>
    <div class="card" id="formCard">
      <h2>Tell us about your project</h2>
      <p class="sub">Fields marked <span style="color:var(--accent-ink)">*</span> are required.</p>
      <form id="f" novalidate>
        <div class="row">
          <div><label for="name">Your name <span class="req">*</span></label>
            <input id="name" name="name" autocomplete="name" required maxlength="200"></div>
          <div><label for="email">Work email <span class="req">*</span></label>
            <input id="email" name="email" type="email" autocomplete="email" required maxlength="320"></div>
        </div>
        <div class="row">
          <div><label for="company">Company</label><input id="company" name="company" autocomplete="organization" maxlength="200"></div>
          <div><label for="website">Website</label><input id="website" name="website" placeholder="https://" maxlength="300"></div>
        </div>
        <div class="row">
          <div><label for="phone">Phone or WhatsApp</label><input id="phone" name="phone" autocomplete="tel" maxlength="40"></div>
          <div><label for="team_size">Team size</label><select id="team_size" name="team_size"><option value="">Select</option></select></div>
        </div>
        <label>What would you like to build?</label>
        <div class="chips" id="needs"></div>
        <label for="budget">Budget range</label>
        <select id="budget" name="budget"><option value="">Select</option></select>
        <label for="message">Describe your goal <span class="req">*</span></label>
        <textarea id="message" name="message" rows="5" required minlength="10" maxlength="5000"
          placeholder="For example: we get 80 WhatsApp messages a day about prices and availability and want an assistant that answers and books appointments into Google Calendar."></textarea>
        <div class="hp" aria-hidden="true"><label for="company_fax">Leave this field empty</label>
          <input id="company_fax" name="company_fax" tabindex="-1" autocomplete="off"></div>
        <div id="err"></div>
        <button id="submit" type="submit">Send request</button>
        <p class="fine">We use your details only to reply to this request. Ask us any time and we will delete them.</p>
      </form>
    </div>

    <div class="card done hidden" id="doneCard">
      <div class="eyebrow">Request received</div>
      <h2>Thank you, we will be in touch shortly.</h2>
      <p class="sub" id="doneText">A confirmation is on its way to your inbox. Someone from our team will reply
        personally within one business day to set up a call.</p>
      <div id="schedule" class="hidden">
        <p class="sub" style="margin-top:14px">Prefer to pick a time right away?</p>
        <a class="btn" id="scheduleLink" href="#" target="_blank" rel="noopener">Choose a time for the call</a>
      </div>
      <a class="btn ghost" style="margin-left:0" href="/">Back to home</a>
    </div>
  </section>
</div>

<script>
const $ = (id) => document.getElementById(id);
const LABELS = {"under_1k":"Under $1,000","1k_5k":"$1,000 to $5,000","5k_20k":"$5,000 to $20,000","20k_plus":"Over $20,000","not_sure":"Not sure yet"};
let TOKEN = null; try { TOKEN = localStorage.getItem("ofd_token"); } catch(e) {}

function opt(sel, value, text){ const o = document.createElement("option"); o.value = value; o.textContent = text; sel.appendChild(o); }

async function init(){
  try {
    const o = await (await fetch("/contact/options")).json();
    for (const [k, label] of Object.entries(o.needs)) {
      const l = document.createElement("label"); l.className = "chip";
      l.innerHTML = '<input type="checkbox" name="needs"><span></span>';
      l.querySelector("input").value = k; l.querySelector("span").textContent = label;
      $("needs").appendChild(l);
    }
    o.team_sizes.forEach(s => opt($("team_size"), s, s + " people"));
    o.budgets.forEach(b => opt($("budget"), b, LABELS[b] || b));
  } catch(e) {}
  const pre = new URLSearchParams(location.search).get("need");
  if (pre) document.querySelectorAll('input[name="needs"]').forEach(c => { if (c.value === pre) c.checked = true; });
  if (TOKEN) {
    try {
      const r = await fetch("/auth/me", {headers: {"Authorization": "Bearer " + TOKEN}});
      if (r.ok) { const me = await r.json(); if (!$("email").value) $("email").value = me.user.email;
        if (!$("name").value && me.user.name) $("name").value = me.user.name;
        if (!$("company").value && me.memberships[0]) $("company").value = me.memberships[0].tenant_name; }
    } catch(e) {}
  }
}

function showError(text){ $("err").innerHTML = ""; const d = document.createElement("div"); d.className = "msg err"; d.textContent = text; $("err").appendChild(d); }

$("f").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  $("err").innerHTML = "";
  const v = (id) => $(id).value.trim();
  if (!v("name") || !v("email") || v("message").length < 10) {
    showError("Please add your name, email and a short description (at least 10 characters).");
    return;
  }
  const body = {
    name: v("name"), email: v("email"), company: v("company") || null, website: v("website") || null,
    phone: v("phone") || null, team_size: v("team_size") || null, budget: v("budget") || null,
    needs: [...document.querySelectorAll('input[name="needs"]:checked')].map(c => c.value),
    message: v("message"), company_fax: $("company_fax").value || null, source: "contact_page"
  };
  const headers = {"Content-Type": "application/json"};
  if (TOKEN) headers["Authorization"] = "Bearer " + TOKEN;
  $("submit").disabled = true; $("submit").textContent = "Sending...";
  try {
    const r = await fetch("/contact", {method: "POST", headers, body: JSON.stringify(body)});
    const j = await r.json().catch(() => ({}));
    if (!r.ok) {
      const d = j.detail && j.detail[0];
      throw new Error((j.error && j.error.message) || (d && (d.msg || "").replace("Value error, ", "")) || "Something went wrong, please try again.");
    }
    $("formCard").classList.add("hidden"); $("doneCard").classList.remove("hidden");
    if (j.scheduling_url) { $("scheduleLink").href = j.scheduling_url; $("schedule").classList.remove("hidden"); }
    window.scrollTo({top: 0, behavior: "smooth"});
  } catch(e) {
    showError(e.message);
  } finally {
    $("submit").disabled = false; $("submit").textContent = "Send request";
  }
});
init();
</script>
</body>
</html>
"""
