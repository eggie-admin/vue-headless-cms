from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = ROOT / "manifests" / "boss-ai.manifest.json"
BASE64_PATH = ROOT / "manifests" / "boss-ai.manifest.b64"


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def manifest_bytes() -> bytes:
    return MANIFEST_PATH.read_bytes()


def manifest_base64() -> str:
    return base64.b64encode(manifest_bytes()).decode("ascii")


def manifest_sha256() -> str:
    return hashlib.sha256(manifest_bytes()).hexdigest()


def verify_base64_copy() -> bool:
    if not BASE64_PATH.is_file():
        return False
    encoded = "".join(BASE64_PATH.read_text(encoding="ascii").split())
    return base64.b64decode(encoded, validate=True) == manifest_bytes()
