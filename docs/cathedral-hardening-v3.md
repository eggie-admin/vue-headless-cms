# Video Forge Cathedral Hardening v3

Status: implementation hardening gate

## Sealed decision

Use the smallest runtime set that preserves the product:

- Node 24 LTS + npm: build/dev tooling for Vue and jQuery only.
- Vue 3.5 + jQuery UI: admin/CMS presentation surface.
- One Python 3 control plane: FastAPI, agent routing, media orchestration, telemetry, persistence adapters and cloud sync.
- Flask 3.1: compatibility-only WSGI island mounted under FastAPI `/compat`; never a second server.
- Ollama: localhost-only edge antenna producing schema-validated decisions. It does not directly execute tools.
- Python policy: authoritative risk and confirmation gate.
- Mixpanel: optional sanitized analytics sink; never source of truth.
- Godot: interactive cage/avatar/cutscene runtime; not duplicated in Node or Flask.

## Why npm

The Samsung Termux lane already carries Node 24 LTS and npm. npm workspaces therefore add no extra package-manager bootstrap. The clean-room web lane is rooted at `apps/package.json`, leaving the inherited root CMS package metadata untouched.

Direct UI dependencies are pinned. CI generates a lock graph for the run, installs from it, and builds the named workspace. A committed clean-room lockfile remains the preferred release gate once generated on a trusted networked build host.

## One Python layer

The runtime must have one HTTP owner. FastAPI is async-first and already provides WebSockets and typed Pydantic contracts. Flask remains only for compatibility with simple WSGI routes and is mounted with Starlette WSGI middleware.

Production does not require a Node server. npm emits `apps/forge-ui/dist`; FastAPI serves it when present.

## Edge mini Ollama antenna

The local model receives no shell capability. It returns `AgentDecision`:

```text
intent
lane: local | cloud
tool
arguments
risk
requires_confirmation
rationale
```

Ollama output is constrained by the Pydantic-generated JSON schema with temperature 0. Python then overwrites risk/confirmation from a deterministic allowlist. If the local decision requests cloud reasoning, or local Ollama fails, the router escalates to the OpenAI agent.

## Mixpanel Headless boundary

Runtime event capture is separate from analysis. Backend telemetry is allowlisted and sanitized before optional Mixpanel delivery. Never send prompt text, filenames, media titles, filesystem paths, credentials, emails, or real names. Headless Mixpanel analysis should discover the actual event schema before querying and must never be treated as application state.

## 10-pass hard gate

1. npm is the sole JS package manager for the clean-room lane.
2. Node 24 LTS is the tablet build target.
3. FastAPI is the single Python control plane.
4. Flask is mounted compatibility, not another server.
5. Ollama decisions are schema constrained.
6. No Node production backend exists.
7. Termux control plane is loopback-only by default.
8. Telemetry excludes prompts, paths and private content.
9. Copilot repository + path instructions are present.
10. CI runs the architecture gate under Node 24.

The executable gate is `python3 scripts/architecture_sanity.py`.

## Mutation boundary

Automatic/read-only: inspect status, route safe queries, set avatar state, pause/resume, read cache state.

Explicit confirmation: finalize output, cleanup cache, upload final media, change credentials, publish, store release, physical mount/eject.

No model receives arbitrary shell authority.

## Release posture

Green means code/contracts/CI passed. It does not mean Android, Godot, Ollama, Mixpanel, FastAPI Cloud, Modal, or store deployment passed unless those surfaces were actually exercised.
