"""The embeddable chat widget script + a demo page. Served by the widget router.

widget.js is fully self-contained (no dependencies), scoped with `ofd-` class names, and derives the API
base from its own <script src> so it works when embedded on any external site.
"""

from __future__ import annotations

WIDGET_JS = """
(function () {
  var script = document.currentScript || (function () {
    var s = document.getElementsByTagName('script');
    for (var i = 0; i < s.length; i++) { if (s[i].src && s[i].src.indexOf('widget.js') > -1) return s[i]; }
    return null;
  })();
  if (!script) return;
  var slug = script.getAttribute('data-agent') || 'demo';
  var color = script.getAttribute('data-color') || '#0f9488';
  var API; try { API = new URL(script.src).origin; } catch (e) { API = ''; }

  var css = ''
    + '.ofd-btn{position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;background:' + color + ';color:#fff;border:0;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.25);font-size:24px;line-height:56px;z-index:2147483000}'
    + '.ofd-panel{position:fixed;bottom:88px;right:20px;width:340px;max-width:calc(100vw - 40px);height:470px;max-height:calc(100vh - 120px);background:#fff;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.3);display:none;flex-direction:column;overflow:hidden;z-index:2147483000;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}'
    + '.ofd-panel.ofd-open{display:flex}'
    + '.ofd-head{background:' + color + ';color:#fff;padding:13px 15px;font-weight:600;font-size:15px}'
    + '.ofd-msgs{flex:1;overflow-y:auto;padding:12px;background:#f7f9f9}'
    + '.ofd-m{margin:6px 0;padding:8px 11px;border-radius:12px;max-width:82%;font-size:14px;line-height:1.45;white-space:pre-wrap;word-wrap:break-word}'
    + '.ofd-bot{background:#fff;border:1px solid #e3e9e9;color:#16242a}'
    + '.ofd-you{background:' + color + ';color:#fff;margin-left:auto}'
    + '.ofd-foot{display:flex;border-top:1px solid #eef2f2}'
    + '.ofd-in{flex:1;border:0;padding:12px;font-size:14px;outline:none}'
    + '.ofd-send{border:0;background:' + color + ';color:#fff;padding:0 16px;cursor:pointer;font-weight:600}'
    + '.ofd-note{font-size:10px;color:#9aa6a6;text-align:center;padding:5px}';
  var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  var btn = document.createElement('button');
  btn.className = 'ofd-btn'; btn.setAttribute('aria-label', 'Open chat'); btn.innerHTML = '&#128172;';
  var panel = document.createElement('div'); panel.className = 'ofd-panel';
  panel.innerHTML =
      '<div class="ofd-head" id="ofd-title">Chat</div>'
    + '<div class="ofd-msgs" id="ofd-msgs"></div>'
    + '<div class="ofd-foot"><input class="ofd-in" id="ofd-in" placeholder="Type a message..." autocomplete="off"/><button class="ofd-send" id="ofd-send">Send</button></div>'
    + '<div class="ofd-note">Powered by OpenFrontDesk</div>';
  document.body.appendChild(btn); document.body.appendChild(panel);

  var msgsEl = panel.querySelector('#ofd-msgs');
  var inEl = panel.querySelector('#ofd-in');
  var history = [];
  var opened = false;

  function add(role, text) {
    var d = document.createElement('div');
    d.className = 'ofd-m ' + (role === 'user' ? 'ofd-you' : 'ofd-bot');
    d.textContent = text; msgsEl.appendChild(d); msgsEl.scrollTop = msgsEl.scrollHeight;
  }
  function typing(on) {
    var t = panel.querySelector('#ofd-typing');
    if (on && !t) {
      t = document.createElement('div'); t.id = 'ofd-typing'; t.className = 'ofd-m ofd-bot';
      t.textContent = '...'; msgsEl.appendChild(t); msgsEl.scrollTop = msgsEl.scrollHeight;
    } else if (!on && t) { t.remove(); }
  }
  function init() {
    fetch(API + '/widget/' + encodeURIComponent(slug) + '/config')
      .then(function (r) { return r.json(); })
      .then(function (c) {
        panel.querySelector('#ofd-title').textContent = c.name || 'Chat';
        add('bot', c.greeting || 'Hi! How can I help?');
      })
      .catch(function () { add('bot', 'Hi! How can I help?'); });
  }
  async function send() {
    var text = inEl.value.trim(); if (!text) return;
    inEl.value = ''; add('user', text); history.push({ role: 'user', content: text }); typing(true);
    try {
      var r = await fetch(API + '/widget/' + encodeURIComponent(slug) + '/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history: history.slice(-8) })
      });
      var d = await r.json(); typing(false);
      var reply = (d && d.reply) || (d && d.error && d.error.message) || 'Sorry, something went wrong.';
      add('bot', reply); history.push({ role: 'assistant', content: reply });
    } catch (e) { typing(false); add('bot', 'Sorry, I could not reach the server.'); }
  }
  btn.addEventListener('click', function () {
    panel.classList.toggle('ofd-open');
    if (!opened) { opened = true; init(); }
  });
  panel.querySelector('#ofd-send').addEventListener('click', send);
  inEl.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); send(); } });
})();
"""

WIDGET_DEMO_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OpenFrontDesk Widget Demo</title>
<style>
 body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:720px;margin:48px auto;
      padding:0 20px;color:#16242a;line-height:1.65;background:#fff}
 code,pre{background:#f2f5f5;border-radius:8px} pre{padding:12px;overflow:auto}
 h1{font-size:1.6rem}
</style>
</head>
<body>
  <h1>Widget demo &mdash; a sample business website</h1>
  <p>The chat bubble in the bottom-right is the embeddable OpenFrontDesk widget, trained on the demo
  clinic's documents. Try asking it <b>"How much is teeth whitening?"</b> or <b>"What are your hours?"</b></p>
  <p>To add it to any website, paste one line (replace the origin with your server):</p>
  <pre>&lt;script src="https://YOUR-SERVER/widget.js" data-agent="demo"&gt;&lt;/script&gt;</pre>
  <p>Leads and bookings captured by the widget appear in the owner's dashboard.</p>
  <script src="/widget.js" data-agent="demo"></script>
</body>
</html>
"""
