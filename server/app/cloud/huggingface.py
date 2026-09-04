from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import quote

import httpx

REPO_ID = re.compile(r"^[A-Za-z0-9._-]{1,100}/[A-Za-z0-9._-]{1,100}$")


def huggingface_readiness() -> dict[str, object]:
    return {
        "role": "model_registry_and_optional_inference",
        "token_configured": bool(os.getenv("HF_TOKEN")),
        "default_model": os.getenv("HF_DEFAULT_MODEL", ""),
        "license_gate": True,
    }


async def model_metadata(repo_id: str) -> dict[str, Any]:
    if not REPO_ID.fullmatch(repo_id):
        raise ValueError("Hugging Face repo id must be owner/model")
    headers = {}
    token = os.getenv("HF_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://huggingface.co/api/models/{quote(repo_id, safe='/')}"
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

    card = data.get("cardData") if isinstance(data.get("cardData"), dict) else {}
    license_id = card.get("license") or data.get("license")
    tags = data.get("tags") if isinstance(data.get("tags"), list) else []
    return {
        "id": data.get("id", repo_id),
        "pipeline_tag": data.get("pipeline_tag"),
        "library_name": data.get("library_name"),
        "license": license_id,
        "private": bool(data.get("private", False)),
        "gated": data.get("gated", False),
        "downloads": data.get("downloads", 0),
        "likes": data.get("likes", 0),
        "tags": [str(tag)[:120] for tag in tags[:50]],
        "license_gate_passed": bool(license_id),
    }
