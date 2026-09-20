"""Minimal, dependency-free browser test page for talking to the agent (Phase 1).

Served at GET /test by the web router. Same-origin fetch of /livekit/token (no CORS). Uses the
livekit-client UMD build from a CDN. This is deliberately plain — the real dashboard comes in Phase 3.
"""

from __future__ import annotations

TEST_PAGE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>OpenFrontDesk — Test Call</title>
<script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
<style>
  :root { --bg:#0b1020; --fg:#e7ecf5; --muted:#9aa6bd; --accent:#4f8cff; --ok:#37d67a; --err:#ff5c5c; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif; background:var(--bg);
         color:var(--fg); display:flex; min-height:100vh; align-items:center; justify-content:center; padding:16px; }
  .card { width:100%; max-width:560px; background:#121a30; border:1px solid #1f2b47; border-radius:16px;
          padding:24px; box-shadow:0 12px 40px rgba(0,0,0,.35); }
  h1 { font-size:20px; margin:0 0 4px; }
  p.sub { color:var(--muted); margin:0 0 20px; font-size:14px; }
  label { font-size:12px; color:var(--muted); display:block; margin-bottom:6px; }
  input { width:100%; padding:10px 12px; border-radius:10px; border:1px solid #26324f; background:#0d1426;
          color:var(--fg); margin-bottom:16px; }
  .row { display:flex; gap:10px; }
  button { flex:1; padding:12px 16px; border:0; border-radius:10px; font-weight:600; cursor:pointer; font-size:15px; }
  #connect { background:var(--accent); color:#fff; }
  #hangup { background:#26324f; color:var(--fg); }
  button:disabled { opacity:.5; cursor:not-allowed; }
  .status { margin:18px 0 8px; font-size:14px; display:flex; align-items:center; gap:8px; }
  .dot { width:10px; height:10px; border-radius:50%; background:var(--muted); }
  .dot.ok { background:var(--ok); } .dot.err { background:var(--err); }
  .transcript { margin-top:14px; background:#0d1426; border:1px solid #1f2b47; border-radius:10px;
                padding:12px; height:200px; overflow:auto; font-size:14px; }
  .line { margin:0 0 8px; } .line .who { color:var(--accent); font-weight:600; }
  .line.agent .who { color:var(--ok); }
  .hint { color:var(--muted); font-size:12px; margin-top:14px; line-height:1.5; }
</style>
</head>
<body>
  <div class="card">
    <h1>🎙️ OpenFrontDesk — Test Call</h1>
    <p class="sub">Talk to your AI receptionist in the browser. Free — no phone number needed.</p>

    <label for="room">Room</label>
    <input id="room" value="ofd-test" />

    <div class="row">
      <button id="connect">📞 Talk to the agent</button>
      <button id="hangup" disabled>Hang up</button>
    </div>

    <div class="status"><span id="dot" class="dot"></span><span id="statusText">Idle</span></div>
    <div class="transcript" id="transcript"></div>

    <p class="hint">Requires: LiveKit configured on the server, the <code>ofd-agent</code> worker running,
    and mic permission. If nothing happens, check the worker logs and your provider keys.</p>
  </div>

<script>
const LK = window.LivekitClient;
const $ = (id) => document.getElementById(id);
let room = null;

function setStatus(text, kind) {
  $("statusText").textContent = text;
  const dot = $("dot"); dot.className = "dot" + (kind ? " " + kind : "");
}
function addLine(who, text, cls) {
  const el = document.createElement("div");
  el.className = "line " + (cls || "");
  el.innerHTML = '<span class="who">' + who + ':</span> <span></span>';
  el.querySelector("span:last-child").textContent = text;
  const t = $("transcript"); t.appendChild(el); t.scrollTop = t.scrollHeight;
}

async function connect() {
  try {
    $("connect").disabled = true;
    setStatus("Requesting token…");
    const roomName = encodeURIComponent($("room").value || "ofd-test");
    const resp = await fetch("/livekit/token?room=" + roomName);
    if (!resp.ok) { const e = await resp.json().catch(() => ({}));
      throw new Error((e.error && e.error.message) || ("token error " + resp.status)); }
    const { url, token } = await resp.json();

    setStatus("Connecting…");
    room = new LK.Room({ adaptiveStream: true, dynacast: true });

    room.on(LK.RoomEvent.TrackSubscribed, (track) => {
      if (track.kind === "audio") { const el = track.attach(); el.autoplay = true; document.body.appendChild(el); }
    });
    room.on(LK.RoomEvent.TranscriptionReceived, (segments, participant) => {
      const isAgent = participant && participant.identity && participant.identity !== "you";
      for (const s of segments) if (s.final) addLine(isAgent ? "Agent" : "You", s.text, isAgent ? "agent" : "");
    });
    room.on(LK.RoomEvent.Disconnected, () => { setStatus("Disconnected", "err"); resetButtons(false); });

    await room.connect(url, token);
    await room.localParticipant.setMicrophoneEnabled(true);
    setStatus("Connected — start talking", "ok");
    $("hangup").disabled = false;
  } catch (err) {
    console.error(err);
    setStatus("Error: " + err.message, "err");
    resetButtons(false);
  }
}

async function hangup() {
  if (room) { await room.disconnect(); room = null; }
  setStatus("Idle"); resetButtons(false);
}
function resetButtons(connected) { $("connect").disabled = connected; $("hangup").disabled = !connected; }

$("connect").addEventListener("click", connect);
$("hangup").addEventListener("click", hangup);
</script>
</body>
</html>
"""
