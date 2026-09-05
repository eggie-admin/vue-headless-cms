# Samsung SM-X400 / Frontend / Widget

This directory is the canonical Samsung SM-X400 frontend widget lane for the build candidate.

The widget is **optional**. It is not embedded into the APK and it does not change the Python-for-Android dependency graph. It stages a Termux:Widget supervisor bundle that can control the local tablet services after installation.

## Provenance

The supervisor design was migrated from `eggie-admin/hydra-shell-android` after merge commit `0f7a58a52a832a2eb04c24f45fde6ded4974ec43`.

## Dependency planes

Build dependencies are intentionally separate from tablet runtime dependencies.

### Candidate/build host

Required:

- Python 3.14+
- Node.js 24.x
- npm 12.0.2

No additional npm package is required for the widget builder. The build/check scripts use the Python standard library only.

### Samsung/Termux runtime

Required for the widget lane:

- Termux
- Termux:Widget
- Python 3

Optional capabilities are detected at runtime and must not make the candidate build fail:

- Termux:API plus the `termux-api` package for wake-lock commands
- AXS on loopback port `8767`
- TigerVNC on loopback port `5901`
- `websockify_rs` / `websockify-rs` on loopback port `6080`
- `hydra-cockpit` on loopback port `8787`
- local Ollama, when the cockpit is used

The supervisor owns only PIDs it starts. It must not use broad `pkill` behavior or bind these services publicly.

## npm wizard

From `apps/`:

```bash
npm run wizard
```

The default path builds the normal Vue frontend. The widget remains opt-in.

Non-interactive examples:

```bash
npm run widget:check
npm run widget:build
npm run candidate:build
npm run candidate:build:widget
npm run wizard -- --widget --dry-run
```

`candidate:build` builds the normal frontend candidate only. `candidate:build:widget` explicitly adds the optional widget bundle.

## Output

The widget builder stages deterministic files under:

```text
dist/samsung-sm-x400/frontend/widget/
```

Runtime dependency availability is reported separately and never smuggled into Ubuntu APK build requirements.
