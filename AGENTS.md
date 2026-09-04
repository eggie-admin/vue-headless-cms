# Video Forge Cathedral Agent Contract

This repository contains a legacy Vue CMS plus a clean-room Video Forge implementation. Treat the clean-room implementation as the active product lane.

## Source of truth

1. GitHub source, schemas, tests, and CI are code truth.
2. FastAPI owns runtime state transitions, agent policy, media orchestration, and API contracts.
3. Godot owns interactive scene state, avatar animation, cutscene playback, and native window composition.
4. Vue owns authoring/admin presentation state only.
5. Ollama and cloud models propose typed decisions; Python policy authorizes them.
6. Mixpanel is analytics only. It is never runtime state and never receives prompts, secrets, media paths, filenames, or private content.

## Runtime doctrine

- Node.js is a build/development tool for the Vue/jQuery surface. Do not add a Node production server.
- Production UI is built to `apps/forge-ui/dist` and may be served by the Python control plane.
- Use one Python ASGI process. FastAPI is the primary application. Flask is compatibility-only and is mounted under `/compat` through WSGI middleware.
- Ollama is localhost-only. Do not bind Ollama or the Python control plane to `0.0.0.0` in tablet scripts.
- jQuery UI may move or resize outer Vue window hosts. It must not own Vue application state or mutate Vue-managed descendants.
- Never execute model-authored shell strings. Expose typed Python tools with deterministic policy.

## Legacy boundary

Do not modify the inherited root `src/`, root `package.json`, or root `package-lock.json` unless the user explicitly requests a legacy migration and licensing/provenance has been resolved.

## Validation

Before declaring a mutation green, run or verify the equivalent of:

```bash
cd apps
npm install --package-lock-only --ignore-scripts --no-audit --no-fund
npm ci --ignore-scripts --no-audit --no-fund
npm run build --workspace=video-forge-ui
cd ..
python3 -m compileall -q server/app scripts tests
python3 scripts/architecture_sanity.py
python3 -m unittest discover -s tests -v
```

Do not claim cloud, Ollama, Mixpanel, Android, or Godot runtime success without direct evidence from those runtimes.
