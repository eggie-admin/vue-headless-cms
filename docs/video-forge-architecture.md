# Video Forge: Samsung USB-C Cache + FFmpeg + AI Frame Pipeline

Status: architecture draft
Branch: `video-forge-usb-cache`

## Goal

Run a local-first video mutation pipeline on the Samsung tablet where:

- Google Drive is durable source/final storage.
- A removable USB-C drive is the high-volume scratch/cache device.
- FFmpeg owns deterministic probe, demux, preview encoding, and final remux.
- AI providers mutate frames through a provider-neutral job contract.
- Vue is the local control room/CMS.
- GitHub is the source, review, CI, and release spine.
- Cache cleanup is bounded by a sentinel root and TTL policy.

## Non-goals

- Do not use Google Drive as a per-frame filesystem.
- Do not delete arbitrary files from removable storage.
- Do not depend on physical OS unmount privileges for normal operation.
- Do not require one AI vendor.
- Do not put API tokens in the repository or browser bundle.

## Runtime topology

```text
Google Drive source MP4
        |
        v
local ingest
        |
        v
USB-C cache root
  VideoForgeCache/
    .video-forge-cache
    jobs/
    preview/
    manifests/
    tmp/
        |
        +--> ffprobe metadata
        +--> FFmpeg CFR PNG frames
        +--> AI frame worker
        +--> preview HLS/fMP4
        +--> final FFmpeg remux
        |
        v
Google Drive final MP4 + manifest
```

## Cache state machine

The UI switch is `Cache Online / Cache Offline`.

States:

- `ABSENT`: no approved removable cache root is visible.
- `AVAILABLE`: approved cache root exists and is writable.
- `ONLINE`: jobs may read/write cache.
- `DRAINING`: stop accepting new writes and close active writers.
- `OFFLINE`: cache root is known but workers are not allowed to use it.
- `LOST`: media disappeared while online; jobs pause instead of failing destructively.

`Cache Offline` is an application state, not a promise that Android physically unmounted the volume.

## Cache root safety contract

A cache root is valid only when all checks pass:

1. Path/URI was explicitly selected or configured.
2. Root is writable.
3. Root contains sentinel file `.video-forge-cache` with a generated installation UUID.
4. Canonical resolved path/URI remains inside the approved root.
5. Cleanup never follows symlinks outside the root.
6. Every job directory contains `job.json` and an installation UUID matching the root sentinel.
7. Active, pinned, exporting, or uploading jobs are never TTL-deleted.

Never issue a recursive delete against an unvalidated path.

## Suggested tablet cache layout

```text
VideoForgeCache/
  .video-forge-cache
  state.sqlite3
  jobs/
    <job-id>/
      source/
        input.mp4
      frames-src/
      frames-ai/
      refs/
      audio/
      preview/
      output/
      manifests/
        ffprobe.json
        frame-timing.json
      job.json
  tmp/
```

## TTL janitor

Each job records:

- `created_at`
- `last_access_at`
- `completed_at`
- `status`
- `pinned`
- `cache_bytes`
- `source_drive_file_id`
- `final_drive_file_id`

Default cleanup policy should be configurable. Suggested initial policy:

- incomplete/active: never auto-delete
- completed and uploaded: eligible after 24 hours
- aborted: eligible after 6 hours
- preview fragments: eligible after 2 hours after finalization
- temporary/transient files: eligible after 1 hour

The janitor runs on service startup and periodically while the service is alive. A future Android wrapper may use WorkManager for persistent periodic cleanup.

Before delete:

1. lock job row
2. confirm status is not active
3. confirm TTL expired
4. confirm no open worker lease
5. confirm canonical job path is below validated cache root
6. delete only that job directory
7. record cleanup event in SQLite

## FFmpeg pipeline

### 1. Probe

```bash
ffprobe -v error -show_format -show_streams -of json input.mp4 > manifests/ffprobe.json
```

### 2. Working-frame normalization

CFR is the default AI working mode because integer frame numbers are deterministic.

```bash
ffmpeg -hide_banner -y \
  -i source/input.mp4 \
  -map 0:v:0 \
  -vf "fps=30" \
  -fps_mode cfr \
  -start_number 0 \
  frames-src/frame_%08d.png
```

Preserve an optional exact-timestamp/VFR mode as a separate advanced path.

### 3. AI worker

Each generated frame uses a provider-neutral request:

```json
{
  "job_id": "...",
  "frame": 1482,
  "source_frame": "frames-src/frame_00001482.png",
  "previous_generated_frame": "frames-ai/frame_00001481.png",
  "scene_reference": "refs/scene-004.png",
  "character_references": [],
  "prompt": "...",
  "negative_prompt": "...",
  "seed": 982417,
  "width": 1920,
  "height": 1080,
  "provider": "configured-provider"
}
```

Provider adapter contract:

```text
prepare(job)
generate(frame_request) -> generated image + metadata
validate(result)
retry_policy(error)
close(job)
```

Secrets stay server-side.

### 4. Frame validation

A generated frame is `DONE` only after checking:

- readable image
- exact expected dimensions
- expected frame number
- nonzero file size
- optional perceptual/continuity checks
- metadata saved to SQLite

### 5. Live preview

Completed frames feed a low-resolution preview encoder. Prefer segmented HLS/fMP4 for progressive in-app playback instead of repeatedly rebuilding one large MP4.

The preview is disposable cache. The final master is not created from preview segments.

### 6. Final remux

```bash
ffmpeg -hide_banner -y \
  -framerate 30 \
  -start_number 0 \
  -i frames-ai/frame_%08d.png \
  -i source/input.mp4 \
  -map 0:v:0 \
  -map 1:a? \
  -map_metadata 1 \
  -c:v libx264 \
  -preset medium \
  -crf 18 \
  -pix_fmt yuv420p \
  -c:a copy \
  -shortest \
  -movflags +faststart \
  output/final.mp4
```

If the original audio codec is not suitable for MP4, transcode audio to AAC.

## Backend services

Suggested Python service modules:

```text
server/
  app.py
  cache_manager.py
  cache_janitor.py
  ffmpeg_service.py
  frame_queue.py
  ai/
    base.py
    provider_openai.py
    provider_google.py
    provider_local.py
  drive_service.py
  preview_service.py
  jobs.py
  models.py
```

Use `asyncio.create_subprocess_exec()` or equivalent argv-based process creation. Avoid building shell command strings from user input.

## API surface

```text
GET  /api/system
GET  /api/cache
POST /api/cache/select
POST /api/cache/online
POST /api/cache/offline
POST /api/cache/cleanup

POST /api/jobs
GET  /api/jobs
GET  /api/jobs/{id}
POST /api/jobs/{id}/start
POST /api/jobs/{id}/pause
POST /api/jobs/{id}/resume
POST /api/jobs/{id}/cancel
POST /api/jobs/{id}/pin

GET  /api/jobs/{id}/frames
GET  /api/jobs/{id}/preview
GET  /api/jobs/{id}/events

POST /api/jobs/{id}/export
POST /api/jobs/{id}/upload
```

Use WebSocket or Server-Sent Events for progress/event streaming.

## Vue control room

Primary panels:

1. `CachePanel`
   - USB cache state
   - free/used space
   - Cache Online/Offline switch
   - TTL policy
   - cleanup now

2. `JobQueue`
   - source
   - stage
   - frame progress
   - provider
   - retry count
   - pause/resume/cancel

3. `VideoPreview`
   - HLS/fMP4 preview
   - source/generated split view
   - scrubber
   - current frame

4. `FrameInspector`
   - source frame
   - generated frame
   - prompt/seed/provider metadata
   - regenerate frame
   - lock/pin frame

5. `PromptStudio`
   - project prompt
   - scene prompts
   - character references
   - provider settings

6. `DrivePanel`
   - source Drive file
   - final upload state
   - checkpoint state

7. `SystemLog`
   - FFmpeg stderr progress
   - AI provider events
   - cache/mount events

## Job state machine

```text
NEW
 -> INGESTING
 -> PROBING
 -> DEMUXING
 -> READY
 -> GENERATING
 -> PREVIEWING
 -> REMUXING
 -> UPLOADING
 -> COMPLETE
```

Exceptional states:

```text
PAUSED
CACHE_LOST
PROVIDER_WAIT
FAILED
CANCELLED
```

Every transition is persisted before the next stage begins.

## GitHub role

GitHub stores:

- source code
- architecture docs
- tests
- CI
- plugin skills/manifests when ready
- release artifacts that do not contain user media or secrets

GitHub does not store:

- generated per-frame cache
- user MP4 masters
- API keys
- OAuth refresh tokens
- private image references

## Test gates

Minimum tests before calling the pipeline green:

1. USB cache disappears during demux -> job pauses safely.
2. USB cache disappears during generation -> job pauses safely.
3. Cache returns -> job resumes from SQLite state.
4. TTL cleanup cannot delete an active job.
5. TTL cleanup rejects a path outside sentinel root.
6. Generated image with wrong dimensions is rejected.
7. AI provider timeout retries without duplicating completed frames.
8. FFmpeg failure captures stderr and job state.
9. Preview can lag generation without blocking the AI worker.
10. Final remux preserves source audio and expected duration.
11. Drive upload failure does not delete local final output.
12. No browser-delivered bundle contains provider secrets.

## Implementation order

1. cache manager + sentinel + SQLite
2. probe/demux/remux service
3. job state machine
4. local fake AI provider for deterministic tests
5. Vue cache/job/preview UI
6. real AI provider adapters
7. Google Drive ingest/export
8. Android removable-storage bridge
9. plugin skills
10. CI + release packaging
