# Video Forge Cathedral Copilot Instructions

Build the Cathedral, not a framework zoo.

- Preserve the clean-room implementation under `apps/forge-ui`, `server`, `godot`, `schemas`, `termux`, and `scripts`.
- Do not mutate the inherited legacy CMS unless explicitly asked.
- Node 24 LTS + npm are the only JavaScript runtime/package-manager lane. Use npm workspaces under `apps/`; do not introduce pnpm, yarn, Bun, or a Node production server.
- FastAPI is the single Python control plane. Flask may exist only as a mounted compatibility application under `/compat`.
- Models return typed decisions. Python policy sets risk and confirmation requirements. Never execute natural-language shell commands.
- Ollama is a local antenna/classifier and may be used for low-risk local decisions. Escalate to cloud reasoning when its structured decision requests the cloud lane or local inference is unavailable.
- Mixpanel telemetry is opt-in, backend-only, sanitized, and non-authoritative.
- Vue owns state; jQuery UI only manipulates outer window geometry.
- Bind tablet development services to loopback by default.
- Prefer reversible changes, schemas, tests, and explicit evidence. CI evidence outranks agent confidence.
