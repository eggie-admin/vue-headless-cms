---
name: samsung-sm-x400-widget-autopilot
description: Use when inspecting, hardening, building, testing, or documenting the Samsung SM-X400 frontend Termux widget lane.
---

# Samsung SM-X400 Widget Autopilot

Use this Skill for the canonical `samsung-sm-x400/frontend/widget` lane on the Samsung build candidate.

## Mission

Keep the widget thin, optional, reproducible, localhost-first, and outside the APK dependency graph. Treat the Termux:Widget supervisor state/ownership contract as stable unless the user explicitly requests a breaking mutation.

## Required discovery before mutation

1. Read the repository `AGENTS.md` and `.github/copilot-instructions.md`.
2. Inspect `samsung-sm-x400-build-candidate` and the exact current head before writing.
3. Read `samsung-sm-x400/frontend/widget/widget.manifest.json` and the files being changed.
4. Keep Ubuntu APK build dependencies, host Python build dependencies, Android app requirements, and Termux widget runtime dependencies separate.
5. Search existing tests and CI gates before adding new build logic.

## Mutation boundary

- Do not put secrets, API keys, signing keys, tokens, recordings, model weights, or credentials into source, logs, manifests, build output, or Git history.
- Do not add root, unrestricted shell execution, arbitrary model-authored commands, hidden telemetry, or public listeners.
- Keep widget-controlled services on loopback.
- Preserve `$HOME/.shortcuts/tasks` and `$HOME/.local/state/hydra-services` ownership/state behavior.
- Never stop unrelated processes or trust stale PIDs.
- Do not make optional Termux/VNC/Ollama capabilities mandatory APK build dependencies.

## Build rule

`npm` is the user-facing build selector; deterministic Python is the orchestrator.

Preferred commands from `apps/`:

```bash
npm run widget:check
npm run widget:build
npm run wizard
npm run candidate:build
npm run candidate:build:widget
```

The normal candidate build must remain valid without the widget. Widget inclusion requires an explicit option.

## Validation

At minimum:

```bash
python3 -m py_compile samsung-sm-x400/frontend/widget/hydra_widget_setup.py
python3 scripts/sm_x400_widget_build.py --check
python3 scripts/sm_x400_build_wizard.py --candidate --with-widget --dry-run
```

When Android/APK code is changed, also run the existing Samsung candidate gates defined by `AGENTS.md` and CI.

## Report states accurately

Distinguish source-updated, widget-staged, candidate-built, CI-green, APK-built, device-qualified, merged, released, submitted, approved, and published states. Never claim a runtime or CI result without evidence.
