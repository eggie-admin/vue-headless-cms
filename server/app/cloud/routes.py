from __future__ import annotations

import secrets

import httpx
from fastapi import APIRouter, Header, HTTPException

from app.cloud.google import (
    archive_gcs_to_drive,
    google_readiness,
    poll_veo,
    submit_veo,
    upload_drive_json,
)
from app.cloud.huggingface import huggingface_readiness, model_metadata
from app.cloud.models import DriveArchiveRequest, DriveJsonUploadRequest, VeoGenerateRequest, VeoStatusRequest
from app.cms.store import write_token
from app.telemetry import emit_event

router = APIRouter(prefix="/api/cloud", tags=["cloud"])


def _require_write_token(provided: str | None) -> None:
    if not provided or not secrets.compare_digest(provided, write_token()):
        raise HTTPException(status_code=401, detail="Cathedral write token required")


def _require_confirmation(provided: str | None, expected: str) -> None:
    if provided != expected:
        raise HTTPException(status_code=409, detail=f"explicit confirmation required: {expected}")


@router.get("/providers")
async def providers() -> dict[str, object]:
    return {
        "ok": True,
        "google": google_readiness(),
        "huggingface": huggingface_readiness(),
    }


@router.post("/google/veo/generate")
async def google_veo_generate(
    request: VeoGenerateRequest,
    x_cathedral_token: str | None = Header(default=None),
    x_cathedral_confirm: str | None = Header(default=None),
) -> dict[str, object]:
    _require_write_token(x_cathedral_token)
    _require_confirmation(x_cathedral_confirm, "google-veo")
    try:
        result = await submit_veo(request)
    except (RuntimeError, ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=f"Google Veo provider failed: {type(exc).__name__}") from exc
    await emit_event(
        "cloud_veo_submitted",
        {
            "provider": "google",
            "duration_seconds": request.duration_seconds,
            "sample_count": request.sample_count,
        },
    )
    return {"ok": True, "result": result}


@router.post("/google/veo/status")
async def google_veo_status(
    request: VeoStatusRequest,
    x_cathedral_token: str | None = Header(default=None),
) -> dict[str, object]:
    _require_write_token(x_cathedral_token)
    try:
        result = await poll_veo(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (RuntimeError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=f"Google Veo status failed: {type(exc).__name__}") from exc
    return {"ok": True, "result": result}


@router.post("/google/drive/archive-gcs")
async def google_drive_archive(
    request: DriveArchiveRequest,
    x_cathedral_token: str | None = Header(default=None),
    x_cathedral_confirm: str | None = Header(default=None),
) -> dict[str, object]:
    _require_write_token(x_cathedral_token)
    _require_confirmation(x_cathedral_confirm, "drive-archive")
    try:
        result = await archive_gcs_to_drive(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (RuntimeError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=f"Google Drive archive failed: {type(exc).__name__}") from exc
    await emit_event("cloud_drive_archived", {"provider": "google", "ok": True})
    return {"ok": True, "file": result}


@router.post("/google/drive/json")
async def google_drive_json(
    request: DriveJsonUploadRequest,
    x_cathedral_token: str | None = Header(default=None),
    x_cathedral_confirm: str | None = Header(default=None),
) -> dict[str, object]:
    _require_write_token(x_cathedral_token)
    _require_confirmation(x_cathedral_confirm, "drive-upload")
    try:
        result = await upload_drive_json(request)
    except (RuntimeError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=f"Google Drive upload failed: {type(exc).__name__}") from exc
    await emit_event("cloud_drive_archived", {"provider": "google", "ok": True})
    return {"ok": True, "file": result}


@router.get("/huggingface/models/{owner}/{model_name}")
async def huggingface_model(owner: str, model_name: str) -> dict[str, object]:
    try:
        metadata = await model_metadata(f"{owner}/{model_name}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Hugging Face provider failed: {type(exc).__name__}") from exc
    await emit_event(
        "hf_model_inspected",
        {
            "provider": "huggingface",
            "license_present": bool(metadata.get("license")),
            "gated": bool(metadata.get("gated")),
        },
    )
    return {"ok": True, "model": metadata}
