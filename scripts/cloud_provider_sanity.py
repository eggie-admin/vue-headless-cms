from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests/cloud-ai.manifest.json"
GOOGLE = ROOT / "server/app/cloud/google.py"
HF = ROOT / "server/app/cloud/huggingface.py"
ROUTES = ROOT / "server/app/cloud/routes.py"
PYPROJECT = ROOT / "server/pyproject.toml"

passes = 0


def check(condition: bool, message: str) -> None:
    global passes
    if not condition:
        raise SystemExit(f"CLOUD_PROVIDER_SANITY_FAIL: {message}")
    passes += 1


manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
google = GOOGLE.read_text(encoding="utf-8")
hf = HF.read_text(encoding="utf-8")
routes = ROUTES.read_text(encoding="utf-8")
pyproject = PYPROJECT.read_text(encoding="utf-8")

check(manifest["authority"] == "python_fastapi", "Python must remain provider authority")
check(manifest["sentry"]["human_identity"] == "google_via_cloudflare_access", "Google sentry drift")
check(manifest["google_cloud"]["auth"]["mode"] == "application_default_credentials_or_workload_identity_federation", "Google auth must be ADC/WIF")
check(manifest["google_cloud"]["vertex_video"]["model_default"] == "veo-3.1-generate-001", "Veo default must be GA 3.1")
check(manifest["google_cloud"]["vertex_video"]["location"] == "us-central1", "Veo location drift")
check(manifest["google_cloud"]["drive"]["role"] == "durable_vault", "Drive must remain vault")
check(manifest["huggingface"]["license_gate_required_before_download_or_runtime_use"] is True, "HF license gate missing")
check(manifest["huggingface"]["automatic_model_download"] is False, "HF must not auto-download models")
check(manifest["secrets"]["https_only"] is True and manifest["secrets"]["query_string_tokens"] is False, "token transport doctrine broken")
check("google-auth[requests]" in pyproject, "google-auth dependency missing")
check("ALLOWED_VEO_MODELS" in google and "veo-3.1-generate-001" in google, "Veo allowlist missing")
check("GOOGLE_APPLICATION_CREDENTIALS" not in google, "do not hard-code service account key paths")
check("Authorization" in google and "Bearer" in google, "Google HTTPS bearer auth missing")
check("supportsAllDrives" in google, "Drive shared-drive compatibility missing")
check("_require_allowed_output_uri" in google, "GCS-to-Drive path boundary missing")
check("https://huggingface.co/api/models/" in hf, "HF API must use fixed HTTPS origin")
check("Authorization" in hf and "HF_TOKEN" in hf, "HF token header gate missing")
check('"google-veo"' in routes and '"drive-archive"' in routes, "explicit cloud confirmations missing")
check("/google/veo/generate" in routes and "/google/drive/archive-gcs" in routes, "cloud routes missing")

combined = "\n".join([MANIFEST.read_text(), google, hf, routes])
for forbidden in ("BEGIN PRIVATE KEY", "sk-proj-", '"private_key"', "?token=", "&token="):
    check(forbidden not in combined, f"secret-like material found: {forbidden}")

print(f"CLOUD_PROVIDER_SANITY_GREEN passes={passes}")
