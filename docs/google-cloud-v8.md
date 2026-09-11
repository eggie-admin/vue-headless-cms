# Google Cloud + Drive + Veo + Hugging Face v8

Video Forge keeps cloud providers behind the Python/FastAPI authority boundary.

## Human sentry

Google identity remains the human IdP inside Cloudflare Access for the `eggiebagelface.art` operator FQDNs. Google OAuth client secrets never enter Vue, Godot, WebView, or the APK.

## Google workload identity

Vertex AI and Google Drive use Application Default Credentials (ADC). Prefer Workload Identity Federation or a Google-hosted workload identity for automation. Do not commit or embed service-account JSON keys. For a local operator development session, use user ADC with only the scopes required by the lane.

Required non-secret configuration:

- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION=us-central1`
- `GOOGLE_VEO_MODEL=veo-3.1-generate-001`
- `GOOGLE_VEO_OUTPUT_GCS_URI=gs://<bucket>/<prefix>`
- `GOOGLE_DRIVE_VAULT_FOLDER_ID=<folder-id>`
- `GOOGLE_DRIVE_MODE=drive_file` or `shared_drive`

## Veo

The default video lane is the GA `veo-3.1-generate-001` endpoint. Video generation is a long-running operation. Requests are bounded to the Cathedral model allowlist, us-central1, 4/6/8 seconds, 9:16 or 16:9, and 720p/1080p. Submission requires the local write token plus `X-Cathedral-Confirm: google-veo`.

Generated media first lands in the configured Google Cloud Storage prefix. The status API accepts only operation names belonging to the configured project/location/model.

## Drive vault

Drive is the durable vault, not render scratch. `drive_file` uses the narrower Drive file scope. `shared_drive` intentionally uses the broader Drive scope and must be configured explicitly. The archive path can only copy objects underneath the configured Veo GCS prefix. Promotion requires `X-Cathedral-Confirm: drive-archive`.

GCS-to-Drive promotion is chunked and resumable so large videos are not loaded into memory as one giant buffer.

## Hugging Face

Hugging Face is a model registry and optional inference supply lane. Model metadata is fetched only from the fixed HTTPS Hub API origin. `HF_TOKEN`, when needed for gated/private metadata, travels only in the Authorization header. The adapter does not automatically download a model. A model must expose license metadata and pass the project license/provenance gate before download, redistribution, fine-tuning, or runtime use.

## Provider API

- `GET /api/cloud/providers`
- `POST /api/cloud/google/veo/generate`
- `POST /api/cloud/google/veo/status`
- `POST /api/cloud/google/drive/archive-gcs`
- `POST /api/cloud/google/drive/json`
- `GET /api/cloud/huggingface/models/{owner}/{model}`

Cost-bearing or external-mutating requests require both the local Cathedral write token and an explicit confirmation header.
