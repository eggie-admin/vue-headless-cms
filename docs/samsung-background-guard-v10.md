# Samsung Background Guard v10

Goal: keep the Samsung development/runtime lane alive without pretending a normal Android app can silently override every OEM power-management policy.

## Normal lane

The Video Forge widget owns one explicit background guard workflow:

- ON: asks Termux to start the Cathedral service and acquires the Termux wake lock.
- OFF: stops the Cathedral and releases the wake lock acquired by the Cathedral control plane.
- SMOKE: probes the real loopback health endpoint.
- GUARD: opens Samsung's official Never sleeping apps list. Add both Termux and Video Forge Cathedral once.
- BENCH: runs the local Samsung benchmark.
- DEV: opens Android Developer Options.
- Tap the VIDEO FORGE title to open the app.

The Samsung Never sleeping apps screen is an OEM policy surface. The normal APK opens it with Samsung's documented `com.samsung.android.sm.ACTION_OPEN_CHECKABLE_LISTACTIVITY` intent using `activity_type=2`. It does not use `WRITE_SECURE_SETTINGS`, accessibility automation, UI scraping, or hidden database writes.

## Privileged development lane

For a dedicated development device with ADB authorization, run:

```bash
scripts/samsung_background_guard_adb.sh
```

That helper restores Android background app-ops to `allow` and places Termux and Video Forge in the active standby bucket. It intentionally does not attempt to modify Samsung's private sleeping-app database.

For fully managed fleets, Samsung Knox / Android Enterprise Device Owner remains the correct automation authority. Shizuku can expose a shell-equivalent development lane, but it must remain explicit and separately authorized.

## Termux wake-lock behavior

The Cathedral control script records when it acquires its wake lock in `~/kai9000/state/cathedral-wakelock`. On OFF it releases the wake lock only when that marker is present and `RELEASE_WAKE_LOCK_ON_STOP=true`.

This profile assumes the Samsung edge device is dedicated to Video Forge. If other Termux jobs intentionally share the global Termux wake lock, set:

```bash
RELEASE_WAKE_LOCK_ON_STOP=false
```

in `~/kai9000/config/widget.env`.

## Battery cost

A held wake lock improves background reliability but consumes more standby power. The control plane therefore ties it to explicit Cathedral ON/OFF state instead of making it permanent.
