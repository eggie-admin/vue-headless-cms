# Video Forge Cathedral v0.6: Vue CMS Full Mutation

The packaged Vue WebView is now a persistent CMS rather than a placeholder cockpit.

## Runtime contract

- Python 3.14/FastAPI owns CMS persistence and validation.
- SQLite stores revisioned CMS documents and an append-only event sequence.
- Read endpoints remain loopback-readable for Godot runtime synchronization.
- CMS writes require `X-Cathedral-Token`. The token is sourced from `VIDEO_FORGE_CMS_TOKEN` or generated once at `state/cms-write-token.txt` with mode 0600 when supported.
- Vue edits canonical JSON payloads and uses optimistic revision checks. Stale writes return HTTP 409.
- Godot `CmsRegistry` consumes `/api/cms/runtime-manifest` and resynchronizes after CMS save/delete bridge messages.
- Android WebView remains origin-locked to `https://appassets.androidplatform.net`.
- Native bridge payloads over 32 KiB are rejected; Godot window and avatar mutations are allowlisted.

## Canonical CMS kinds

`ui_manifest`, `scene_manifest`, `content`, `character_bible`, `visual_bible`, `asset_manifest`, `cutscene`.

The CMS is still local-first. Cloud providers may reason about proposed mutations, but Python policy and explicit write authorization remain authoritative.
