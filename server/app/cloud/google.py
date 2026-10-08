from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from importlib.util import find_spec
from typing import Any
from urllib.parse import quote

import httpx

from app.cloud.models import DriveArchiveRequest, DriveJsonUploadRequest, VeoGenerateRequest, VeoStatusRequest

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
ALLOWED_VEO_MODELS = {"veo-3.1-generate-001", "veo-3.1-fast-generate-001"}
ALLOWED_LOCATION = "us-central1"
CHUNK_BYTES = 8 * 1024 * 1024


def google_readiness() -> dict[str, object]:
    return {
        "auth_mode": "adc_or_workload_identity_federation",
        "google_auth_installed": find_spec("google.auth") is not None,
        "project_configured": bool(os.getenv("GOOGLE_CLOUD_PROJECT")),
        "veo_output_configured": bool(os.getenv("GOOGLE_VEO_OUTPUT_GCS_URI")),
        "drive_folder_configured": bool(os.getenv("GOOGLE_DRIVE_VAULT_FOLDER_ID")),
        "drive_mode": os.getenv("GOOGLE_DRIVE_MODE", "drive_file"),
        "veo_model": os.getenv("GOOGLE_VEO_MODEL", "veo-3.1-generate-001"),
        "location": os.getenv("GOOGLE_CLOUD_LOCATION", ALLOWED_LOCATION),
    }


def _drive_scope() -> str:
    mode = os.getenv("GOOGLE_DRIVE_MODE", "drive_file").strip().lower()
    if mode == "shared_drive":
        return DRIVE_SCOPE
    if mode != "drive_file":
        raise RuntimeError("GOOGLE_DRIVE_MODE must be drive_file or shared_drive")
    return DRIVE_FILE_SCOPE


def _load_access_token(scopes: list[str]) -> tuple[str, str | None]:
    import google.auth
    from google.auth.transport.requests import Request

    credentials, adc_project = google.auth.default(scopes=scopes)
    if not credentials.valid:
        credentials.refresh(Request())
    token = getattr(credentials, "token", None)
    if not token:
        raise RuntimeError("Google ADC did not produce an access token")
    return token, adc_project


async def _access_token(scopes: list[str]) -> tuple[str, str | None]:
    return await asyncio.to_thread(_load_access_token, scopes)


def _google_config() -> tuple[str, str, str, str]:
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
    output = os.getenv("GOOGLE_VEO_OUTPUT_GCS_URI", "").strip().rstrip("/")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", ALLOWED_LOCATION).strip()
    model = os.getenv("GOOGLE_VEO_MODEL", "veo-3.1-generate-001").strip()

    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not configured")
    if location != ALLOWED_LOCATION:
        raise RuntimeError(f"Veo 3.1 Cathedral lane is pinned to {ALLOWED_LOCATION}")
    if model not in ALLOWED_VEO_MODELS:
        raise RuntimeError("GOOGLE_VEO_MODEL is not in the Cathedral allowlist")
    if not output.startswith("gs://") or ".." in output:
        raise RuntimeError("GOOGLE_VEO_OUTPUT_GCS_URI must be a canonical gs:// prefix")
    return project, location, model, output


def build_veo_request(request: VeoGenerateRequest) -> tuple[str, dict[str, Any]]:
    project, location, model, output = _google_config()
    url = (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}"
        f"/publishers/google/models/{model}:predictLongRunning"
    )
    instance: dict[str, Any] = {"prompt": request.prompt}
    if request.image_gcs_uri:
        instance["image"] = {"gcsUri": request.image_gcs_uri, "mimeType": request.image_mime_type}
    if request.last_frame_gcs_uri:
        instance["lastFrame"] = {
            "gcsUri": request.last_frame_gcs_uri,
            "mimeType": request.last_frame_mime_type,
        }

    parameters: dict[str, Any] = {
        "storageUri": output,
        "sampleCount": request.sample_count,
        "durationSeconds": request.duration_seconds,
        "aspectRatio": request.aspect_ratio,
        "resolution": request.resolution,
        "generateAudio": request.generate_audio,
        "enhancePrompt": request.enhance_prompt,
        "personGeneration": request.person_generation,
    }
    if request.negative_prompt:
        parameters["negativePrompt"] = request.negative_prompt
    if request.seed is not None:
        parameters["seed"] = request.seed
    return url, {"instances": [instance], "parameters": parameters}


async def submit_veo(request: VeoGenerateRequest) -> dict[str, Any]:
    project, location, model, output = _google_config()
    token, _ = await _access_token([CLOUD_PLATFORM_SCOPE])
    url, body = build_veo_request(request)
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
        )
        response.raise_for_status()
        data = response.json()
    operation_name = data.get("name")
    if not isinstance(operation_name, str):
        raise RuntimeError("Vertex AI did not return an operation name")
    return {
        "provider": "google_vertex_veo",
        "project": project,
        "location": location,
        "model": model,
        "operation_name": operation_name,
        "output_gcs_prefix": output,
    }


async def poll_veo(request: VeoStatusRequest) -> dict[str, Any]:
    project, location, model, _ = _google_config()
    prefix = f"projects/{project}/locations/{location}/publishers/google/models/{model}/operations/"
    if not request.operation_name.startswith(prefix):
        raise ValueError("operation_name does not belong to the configured Veo project/model")
    if not re.fullmatch(r"[A-Za-z0-9_./:-]+", request.operation_name):
        raise ValueError("operation_name contains invalid characters")
    token, _ = await _access_token([CLOUD_PLATFORM_SCOPE])
    url = (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}"
        f"/publishers/google/models/{model}:fetchPredictOperation"
    )
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"operationName": request.operation_name},
        )
        response.raise_for_status()
        return response.json()


def _vault_folder() -> str:
    folder = os.getenv("GOOGLE_DRIVE_VAULT_FOLDER_ID", "").strip()
    if not folder or not re.fullmatch(r"[A-Za-z0-9_-]{8,200}", folder):
        raise RuntimeError("GOOGLE_DRIVE_VAULT_FOLDER_ID is not configured or invalid")
    return folder


def _drive_metadata(name: str, mime_type: str) -> dict[str, Any]:
    return {"name": name, "mimeType": mime_type, "parents": [_vault_folder()]}


async def upload_drive_json(request: DriveJsonUploadRequest) -> dict[str, Any]:
    token, _ = await _access_token([_drive_scope()])
    boundary = f"cathedral-{uuid.uuid4().hex}"
    metadata = json.dumps(_drive_metadata(request.name, "application/json"), separators=(",", ":"))
    payload = json.dumps(request.payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    body = (
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{metadata}\r\n"
        f"--{boundary}\r\nContent-Type: application/json\r\n\r\n{payload}\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    url = (
        "https://www.googleapis.com/upload/drive/v3/files"
        "?uploadType=multipart&supportsAllDrives=true&fields=id,name,mimeType,parents,webViewLink"
    )
    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
            content=body,
        )
        response.raise_for_status()
        return response.json()


def _parse_gcs_uri(gcs_uri: str) -> tuple[str, str]:
    if not gcs_uri.startswith("gs://") or ".." in gcs_uri:
        raise ValueError("invalid GCS URI")
    rest = gcs_uri[5:]
    bucket, sep, object_name = rest.partition("/")
    if not sep or not bucket or not object_name:
        raise ValueError("GCS URI must include bucket and object")
    return bucket, object_name


def _require_allowed_output_uri(gcs_uri: str) -> None:
    _, _, _, output_prefix = _google_config()
    prefix = output_prefix.rstrip("/") + "/"
    if not gcs_uri.startswith(prefix):
        raise ValueError("GCS object is outside the configured Veo output prefix")


async def archive_gcs_to_drive(request: DriveArchiveRequest) -> dict[str, Any]:
    _require_allowed_output_uri(request.gcs_uri)
    bucket, object_name = _parse_gcs_uri(request.gcs_uri)
    token, _ = await _access_token([CLOUD_PLATFORM_SCOPE, _drive_scope()])
    auth = {"Authorization": f"Bearer {token}"}
    encoded_object = quote(object_name, safe="")
    metadata_url = f"https://storage.googleapis.com/storage/v1/b/{quote(bucket, safe='')}/o/{encoded_object}"
    media_url = metadata_url + "?alt=media"

    async with httpx.AsyncClient(timeout=120.0) as client:
        meta_response = await client.get(metadata_url, headers=auth, params={"fields": "size,contentType,name"})
        meta_response.raise_for_status()
        source = meta_response.json()
        size = int(source["size"])
        mime_type = source.get("contentType") or "video/mp4"

        session_response = await client.post(
            "https://www.googleapis.com/upload/drive/v3/files",
            params={
                "uploadType": "resumable",
                "supportsAllDrives": "true",
                "fields": "id,name,mimeType,parents,webViewLink",
            },
            headers={
                **auth,
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": mime_type,
                "X-Upload-Content-Length": str(size),
            },
            json=_drive_metadata(request.name, mime_type),
        )
        session_response.raise_for_status()
        session_url = session_response.headers.get("Location")
        if not session_url or not session_url.startswith("https://"):
            raise RuntimeError("Drive did not return an HTTPS resumable upload URL")

        offset = 0
        final: dict[str, Any] | None = None
        while offset < size:
            end = min(offset + CHUNK_BYTES, size) - 1
            chunk_response = await client.get(
                media_url,
                headers={**auth, "Range": f"bytes={offset}-{end}"},
            )
            if chunk_response.status_code not in {200, 206}:
                chunk_response.raise_for_status()
            chunk = chunk_response.content
            if not chunk:
                raise RuntimeError("GCS returned an empty upload chunk")
            actual_end = offset + len(chunk) - 1
            drive_response = await client.put(
                session_url,
                headers={
                    "Content-Type": mime_type,
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {offset}-{actual_end}/{size}",
                },
                content=chunk,
            )
            if drive_response.status_code == 308:
                offset = actual_end + 1
                continue
            drive_response.raise_for_status()
            final = drive_response.json()
            offset = size

    if final is None:
        raise RuntimeError("Drive resumable upload ended without a final file resource")
    return final
