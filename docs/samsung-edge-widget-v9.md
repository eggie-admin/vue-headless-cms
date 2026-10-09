# Samsung Edge Widget v9

Video Forge uses a local home-screen widget as a control surface for the Samsung edge lane.

## Roles

- SM-X400: interactive development tablet running Godot + packaged Vue WebView.
- Galaxy S10 Lite: headless edge node by default. FastAPI/FFmpeg/Ollama stay local; X11/VNC stay off unless explicitly requested.

## Widget controls

- ON: asks Termux to start the allowlisted `~/kai9000/bin/cathedral-control start` action.
- OFF: stops the Cathedral service.
- SMOKE: probes `http://127.0.0.1:8000/api/health` from the Android widget and reports the current System WebView major version.
- BENCH: runs the local Samsung benchmark and writes `~/kai9000/state/samsung-benchmark.json`.
- DEV: opens Android Developer Options. It does not attempt to read or modify protected global developer settings.
- OPEN: launches Video Forge Cathedral.

Explicit ON/OFF buttons are intentional. A blind toggle can become stale when Android kills or suspends the Termux process.

## One-time Termux setup

```bash
cd ~/kai9000-forge
termux/install-samsung-edge.sh --enable-widget-control
```

This installs the runit service scaffold and sets `allow-external-apps=true`. Android still requires a separate user grant:

`Settings > Apps > Video Forge Cathedral > Permissions > Additional permissions > Run commands in Termux environment`

The dual gate is deliberate. Remove the permission or set `allow-external-apps=false` to disable widget-to-Termux command execution.

For optional boot start:

```bash
termux/install-samsung-edge.sh --enable-widget-control --autostart
```

The generated `~/.termux/boot/video-forge-cathedral` script requires the Termux:Boot companion app.

## Kiosk doctrine

The default app can enter an immersive full-screen shell, but it does not claim Device Owner privileges. Real Android lock-task kiosk control requires a Device Policy Controller / Device Owner or an affiliated profile owner. Samsung Knox/ProKiosk is an optional enterprise lane, not a hidden privilege escalation.

## Developer mode doctrine

Normal third-party apps cannot safely act as a Developer Options master switch. The baseline only opens the official Developer Options screen. Automated enable/disable belongs to an explicitly managed Knox/Android Enterprise lane or an intentionally privileged Shizuku/ADB development lane.

## WebView channels

- Stable: production default.
- Beta: primary compatibility test lane.
- Dev: secondary forward-compatibility test lane.
- Canary: manual-only fault finding.

Use WebView DevTools to change providers. Do not bundle or sideload a System WebView implementation inside the Video Forge APK.

## Rendering

Godot Mobile is the primary Android renderer, giving the Samsung lane the Vulkan path. Physical Samsung smoke remains authoritative. If a device/driver cannot sustain the RenderingDevice path, keep a Compatibility fallback build/profile rather than forcing Vulkan blindly.

## Benchmarks

Smoke:

```bash
npm --prefix apps run samsung:smoke
```

Full local benchmark:

```bash
npm --prefix apps run samsung:bench
```

The full pass records device properties, current WebView provider, Vulkan properties/vulkaninfo when available, Python/Node/npm/FFmpeg/Godot versions, FastAPI/Ollama latency, CPU SHA-256 throughput, a 32 MiB fsync write test, and a short deterministic FFmpeg H.264 encode.

No public network target is used by the benchmark.
