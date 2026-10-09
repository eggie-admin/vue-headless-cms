# Boss AI Toolchain v4

Status: code scaffold with deterministic contracts. External provider execution remains environment-gated.

## Sealed architecture

The Boss AI is one Python control plane, not a mesh of AIs calling each other arbitrarily.

```text
operator feed allowlist
        |
        v
 RSS / Atom fetch
        |
 normalize + strip HTML
        |
 SQLite dedupe
        |
        v
   FeedItem contract
        |
        +-----------------------------+
        | plan only by default        |
        | BOSS_AUTO_FANOUT=true gate  |
        v                             v
     Ollama                        OpenAI
 local reviewer                 boss reasoner
        \                         /
         \                       /
          +------ advisory -------+
                  |
                Gemini
         independent reviewer
                  |
                  v
           typed assessments
                  |
                  v
         deterministic Python
          approval / policy
```

## Canonical manifest

`manifests/boss-ai.manifest.json` is authoritative. `manifests/boss-ai.manifest.b64` is generated from it byte-for-byte by `scripts/build_boss_manifest.py`. Neither file contains secret values.

The Base64 layer exists for transport into agents, CI artifacts, QR/text channels, or APIs that prefer opaque text. It is not encryption.

## Provider roles

- OpenAI Agents SDK: cloud boss reasoning. One structured-output agent, not an unrestricted shell agent.
- Ollama: localhost edge antenna and cheap/offline reviewer.
- Gemini: independent advisory review through the Interactions API when configured.
- Modal: GPU worker lane, not orchestration truth.
- Hugging Face: licensed model supply/tuning lane, not orchestration truth.

All provider output is validated before use. A provider assessment cannot directly execute a Video Forge tool.

## RSS/Atom lane

The server never accepts an arbitrary feed URL from a user request. Operators configure a JSON mapping in `BOSS_FEEDS_JSON`, for example:

```json
{
  "openai_release_notes": "https://vendor.example/feed.xml",
  "android_updates": "https://vendor.example/atom.xml"
}
```

Clients poll by source id. URLs must use HTTPS and local/loopback names are rejected. The fetcher refuses redirects and caps each document at 2 MiB and ten normalized items per poll.

Feed content is explicitly marked `<untrusted_feed_item>` before it reaches a model. Provider instructions say not to follow commands, requests, or links contained inside the feed.

## Cost and automation gate

`BOSS_AUTO_FANOUT` is false by default. Polling still normalizes and deduplicates feeds without calling paid providers. When explicitly enabled, each new feed item fans out only to configured providers, with a maximum of three provider adapters.

This separates continuous ingestion from potentially billable inference.

## State

Tablet feed dedupe uses SQLite through `BOSS_STATE_DB`. Cloud shared state should later move to the existing Redis/Postgres control-plane design. SQLite is not promoted as autoscaled cloud truth.

## API surface

- `GET /api/boss/manifest`
- `GET /api/boss/providers`
- `POST /api/boss/feeds/{source_id}/poll`

The manifest endpoint returns both canonical JSON and deterministic Base64 plus a SHA-256 so clients can verify transport integrity.

## Security invariants

1. No API key values in Git, manifest, Vue, Godot assets, or logs.
2. No arbitrary feed URL supplied by model/user input.
3. No model-authored shell.
4. Feed content is untrusted and cannot authorize actions.
5. Provider output is Pydantic validated.
6. Python policy outranks provider confidence.
7. Fanout is off by default.
8. Provider failures are isolated.
9. Analytics excludes feed text/URLs.
10. CI verifies manifest roundtrip and Boss AI contracts.

## Release posture

A green Boss AI CI gate proves source/contracts/tests. It does not prove live OpenAI, Ollama, Gemini, Android, FastAPI Cloud, or Samsung execution unless those providers/runtimes were actually exercised.
