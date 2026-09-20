"""Static-ish web routes: a tiny landing page and the browser test-call page."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ofd import __version__
from ofd.api.dashboard import DASHBOARD_HTML
from ofd.api.testpage import TEST_PAGE_HTML

router = APIRouter(tags=["web"])

_LANDING = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>OpenFrontDesk</title>
<style>
 body{{margin:0;font-family:system-ui,sans-serif;background:#0b1020;color:#e7ecf5;
      display:flex;min-height:100vh;align-items:center;justify-content:center;text-align:center}}
 a{{color:#4f8cff}} .box{{max-width:520px;padding:24px}}
 .btn{{display:inline-block;margin:8px;padding:12px 18px;border-radius:10px;background:#4f8cff;color:#fff;
       text-decoration:none;font-weight:600}}
 .ghost{{background:#26324f}}
</style></head>
<body><div class="box">
 <h1>🎙️ OpenFrontDesk</h1>
 <p>Open-source AI voice receptionist · v{__version__}</p>
 <a class="btn" href="/app">🖥️ Dashboard</a>
 <a class="btn" href="/test">📞 Try a test call</a>
 <a class="btn ghost" href="/docs">API docs</a>
</div></body></html>"""


@router.get("/", response_class=HTMLResponse)
async def landing() -> str:
    return _LANDING


@router.get("/app", response_class=HTMLResponse)
async def dashboard() -> str:
    return DASHBOARD_HTML


@router.get("/test", response_class=HTMLResponse)
async def test_page() -> str:
    return TEST_PAGE_HTML
