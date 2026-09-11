from __future__ import annotations

from flask import Flask, jsonify

compat_app = Flask("video_forge_compat")


@compat_app.get("/health")
def health():
    return jsonify(ok=True, boundary="compat-only", server="fastapi-mounted-wsgi")
