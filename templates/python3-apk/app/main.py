from __future__ import annotations

import json
import os
import platform
import time

from flask import Flask, Response

app = Flask(__name__)
STARTED = time.time()


@app.get("/")
def index() -> str:
    return """<!doctype html>
<html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Samsung SM-X400 Python</title></head>
<body style='font-family:sans-serif;background:#101318;color:#f5f7fa;padding:24px'>
<h1>Samsung SM-X400 Python</h1>
<p>Python-for-Android WebView template is running.</p>
<pre id='health'>loading...</pre>
<script>
fetch('/health').then(r => r.json()).then(v => {
  document.getElementById('health').textContent = JSON.stringify(v, null, 2)
})
</script></body></html>"""


@app.get("/health")
def health() -> Response:
    payload = {
        "ok": True,
        "service": "samsung-sm-x400-python-template",
        "python": platform.python_version(),
        "pid": os.getpid(),
        "uptime_s": round(time.time() - STARTED, 2),
    }
    return Response(json.dumps(payload, sort_keys=True), mimetype="application/json")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765, threaded=False, use_reloader=False)
