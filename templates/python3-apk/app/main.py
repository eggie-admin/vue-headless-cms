from __future__ import annotations

import json
import os
import platform
import socket
import time
import urllib.error
import urllib.request
from typing import Any

from flask import Flask, Response, request

app = Flask(__name__)
STARTED = time.time()
ALTAR = "http://127.0.0.1:8797"
MAGIC_PREFIX = "/api/magic/"
MAX_BODY = 64 * 1024
PROBES = {
    "vnc": ("127.0.0.1", 5901),
    "websocket": ("127.0.0.1", 6080),
    "acodex": ("127.0.0.1", 8767),
    "magic": ("127.0.0.1", 8797),
}


def _json(payload: Any, status: int = 200) -> Response:
    return Response(
        json.dumps(payload, sort_keys=True),
        status=status,
        mimetype="application/json",
    )


def _tcp_probe(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except OSError:
        return False


def _altar_request(path: str, method: str = "GET", payload: Any | None = None) -> tuple[int, Any]:
    if not path.startswith(MAGIC_PREFIX):
        return 403, {"ok": False, "detail": "Only the typed magic API may be proxied"}

    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        if len(body) > MAX_BODY:
            return 413, {"ok": False, "detail": "Request exceeds 64 KiB limit"}
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        ALTAR + path,
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            raw = response.read(MAX_BODY + 1)
            if len(raw) > MAX_BODY:
                return 502, {"ok": False, "detail": "Altar response exceeded 64 KiB limit"}
            try:
                return response.status, json.loads(raw.decode("utf-8"))
            except Exception:
                return response.status, {"ok": True, "text": raw.decode("utf-8", "replace")}
    except urllib.error.HTTPError as exc:
        raw = exc.read(MAX_BODY)
        try:
            detail = json.loads(raw.decode("utf-8"))
        except Exception:
            detail = {"detail": raw.decode("utf-8", "replace")}
        return exc.code, detail
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 503, {
            "ok": False,
            "detail": "KAI9000 magic altar is offline",
            "altar": ALTAR,
            "error": type(exc).__name__,
        }


INDEX = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>KAI9000 ULTIMA</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif}
body{margin:0;background:#080b12;color:#eef4ff}
header{padding:18px 18px 10px;background:#0d1322;border-bottom:1px solid #223154}
h1{margin:0;font-size:1.35rem}.sub{opacity:.72;font-size:.9rem;margin-top:5px}
main{padding:14px;display:grid;gap:12px}
.card{background:#101827;border:1px solid #26395e;border-radius:14px;padding:13px}
.row{display:flex;gap:8px;flex-wrap:wrap}.grow{flex:1 1 220px}
input,textarea,select,button{font:inherit;box-sizing:border-box;width:100%;border-radius:10px;border:1px solid #30466e;background:#090e18;color:#eef4ff;padding:10px}
textarea{min-height:94px;resize:vertical}button{cursor:pointer;font-weight:700}
button.primary{background:#153967}button.danger{background:#57202c}
.badges{display:flex;gap:6px;flex-wrap:wrap}.badge{padding:5px 8px;border-radius:999px;background:#17243a;font-size:.78rem}
.green{background:#123b2c}.red{background:#491d27}.amber{background:#4a3812}
pre{white-space:pre-wrap;word-break:break-word;background:#070a10;border-radius:10px;padding:10px;max-height:38vh;overflow:auto}
.small{font-size:.82rem;opacity:.75}
</style>
<script src="/static/jquery.min.js"></script>
<script defer src="/static/cockpit.js"></script>
</head>
<body>
<header>
  <h1>🔷 KAI9000 ULTIMA</h1>
  <div class="sub">jQuery cockpit · Python 3 bridge · typed FastAPI altar · Crown-gated mutation</div>
</header>
<main>
  <section class="card">
    <div class="badges" id="serviceBadges"><span class="badge amber">probing altar…</span></div>
    <div class="small" id="runtimeLine"></div>
  </section>

  <section class="card">
    <h3>Magic Chat</h3>
    <textarea id="chatPrompt" placeholder="Ask Lum to inspect, reason, or prepare a typed coding mutation."></textarea>
    <button class="primary" id="chatSend">CAST CHAT</button>
  </section>

  <section class="card">
    <h3>Spell Cast</h3>
    <div class="row">
      <div class="grow"><select id="spell"></select></div>
      <div class="grow"><input id="castId" placeholder="cast id" readonly></div>
    </div>
    <textarea id="spellArgs" placeholder='{"path":"README.md"}'>{}</textarea>
    <div class="row">
      <div class="grow"><button id="prepare">PREPARE</button></div>
      <div class="grow"><button id="approve">CROWN APPROVE</button></div>
      <div class="grow"><button class="primary" id="execute">EXECUTE</button></div>
      <div class="grow"><button class="danger" id="rollback">ROLLBACK</button></div>
    </div>
  </section>

  <section class="card">
    <h3>Result</h3>
    <pre id="out">ULTIMA cockpit booting…</pre>
  </section>
</main>
</body>
</html>
"""


@app.get("/")
def index() -> str:
    return INDEX


@app.get("/health")
def health() -> Response:
    services = {name: _tcp_probe(host, port) for name, (host, port) in PROBES.items()}
    return _json(
        {
            "ok": True,
            "service": "kai9000-ultima-apk",
            "version": "1.0.0",
            "python": platform.python_version(),
            "pid": os.getpid(),
            "uptime_s": round(time.time() - STARTED, 2),
            "altar": ALTAR,
            "services": services,
            "credential_policy": "apk_contains_no_provider_credentials",
        }
    )


@app.get("/api/magic/spells")
def magic_spells() -> Response:
    status, payload = _altar_request("/api/magic/spells")
    return _json(payload, status)


@app.post("/api/magic/chat")
def magic_chat() -> Response:
    payload = request.get_json(silent=True) or {}
    status, result = _altar_request("/api/magic/chat", "POST", payload)
    return _json(result, status)


@app.post("/api/magic/cast/prepare")
def magic_prepare() -> Response:
    payload = request.get_json(silent=True) or {}
    status, result = _altar_request("/api/magic/cast/prepare", "POST", payload)
    return _json(result, status)


@app.post("/api/magic/cast/<cast_id>/approve")
def magic_approve(cast_id: str) -> Response:
    payload = request.get_json(silent=True) or {}
    status, result = _altar_request(f"/api/magic/cast/{cast_id}/approve", "POST", payload)
    return _json(result, status)


@app.post("/api/magic/cast/<cast_id>/execute")
def magic_execute(cast_id: str) -> Response:
    status, result = _altar_request(f"/api/magic/cast/{cast_id}/execute", "POST", {})
    return _json(result, status)


@app.post("/api/magic/cast/<cast_id>/rollback")
def magic_rollback(cast_id: str) -> Response:
    payload = request.get_json(silent=True) or {}
    status, result = _altar_request(f"/api/magic/cast/{cast_id}/rollback", "POST", payload)
    return _json(result, status)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765, threaded=False, use_reloader=False)
