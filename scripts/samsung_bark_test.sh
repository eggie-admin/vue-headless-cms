#!/usr/bin/env bash
set -euo pipefail

# BARK = Background App Resilience Kill.
# This intentionally uses `am kill`, never `am force-stop`, so the test models
# reclaimable background-process death rather than Android's explicit stopped state.

ADB="${ADB:-adb}"
CURL="${CURL:-curl}"
CYCLES="${BARK_CYCLES:-3}"
RECOVERY_TIMEOUT="${BARK_RECOVERY_TIMEOUT:-30}"
POLL_INTERVAL="${BARK_POLL_INTERVAL:-2}"
HEALTH_PORT="${BARK_HEALTH_PORT:-18000}"
TERMUX_PACKAGE="${TERMUX_PACKAGE:-com.termux}"
APP_PACKAGE="${VIDEO_FORGE_PACKAGE:-art.eggiebagelface.videoforge.dev}"
OUTPUT="${BARK_OUTPUT:-$HOME/kai9000/state/samsung-bark.json}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for command in "$ADB" "$CURL" python3; do
  command -v "$command" >/dev/null 2>&1 || { echo "missing command: $command" >&2; exit 2; }
done

case "$CYCLES" in
  ''|*[!0-9]*) echo "BARK_CYCLES must be an integer" >&2; exit 2 ;;
esac
if (( CYCLES < 1 || CYCLES > 20 )); then
  echo "BARK_CYCLES must be between 1 and 20" >&2
  exit 2
fi

"$ADB" get-state >/dev/null
bash "$ROOT/scripts/samsung_background_guard_adb.sh" >/dev/null
"$ADB" forward "tcp:$HEALTH_PORT" tcp:8000 >/dev/null

cleanup() {
  "$ADB" forward --remove "tcp:$HEALTH_PORT" >/dev/null 2>&1 || true
}
trap cleanup EXIT

health_ok() {
  "$CURL" --fail --silent --show-error --max-time 2 "http://127.0.0.1:$HEALTH_PORT/api/health" >/dev/null 2>&1
}

wait_for_health() {
  local waited=0
  while (( waited < RECOVERY_TIMEOUT )); do
    if health_ok; then
      printf '%s' "$waited"
      return 0
    fi
    sleep "$POLL_INTERVAL"
    waited=$(( waited + POLL_INTERVAL ))
  done
  printf '%s' "$waited"
  return 1
}

app_foreground() {
  "$ADB" shell dumpsys activity activities 2>/dev/null \
    | grep -E 'mResumedActivity|topResumedActivity' \
    | grep -F "$APP_PACKAGE" >/dev/null 2>&1
}

wait_for_app_foreground() {
  local waited=0
  while (( waited < RECOVERY_TIMEOUT )); do
    if app_foreground; then
      printf '%s' "$waited"
      return 0
    fi
    sleep "$POLL_INTERVAL"
    waited=$(( waited + POLL_INTERVAL ))
  done
  printf '%s' "$waited"
  return 1
}

if ! health_ok; then
  echo "BARK preflight failed: FastAPI is not healthy before kill test" >&2
  exit 3
fi

mkdir -p "$(dirname "$OUTPUT")"
passed=0
failed=0
health_recovery_csv=""
ui_recovery_csv=""

for (( cycle=1; cycle<=CYCLES; cycle++ )); do
  echo "BARK cycle $cycle/$CYCLES"

  # Put UI in the background before asking ActivityManager to reclaim processes.
  "$ADB" shell input keyevent KEYCODE_HOME >/dev/null 2>&1 || true
  sleep 1

  "$ADB" shell am kill "$APP_PACKAGE" >/dev/null 2>&1 || true
  "$ADB" shell am kill "$TERMUX_PACKAGE" >/dev/null 2>&1 || true

  health_recovery="$(wait_for_health)" || health_ok_after=false
  health_ok_after="${health_ok_after:-true}"

  "$ADB" shell monkey -p "$APP_PACKAGE" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
  ui_recovery="$(wait_for_app_foreground)" || ui_ok_after=false
  ui_ok_after="${ui_ok_after:-true}"

  if [[ "$health_ok_after" == "true" && "$ui_ok_after" == "true" ]]; then
    passed=$(( passed + 1 ))
  else
    failed=$(( failed + 1 ))
  fi

  if [[ -n "$health_recovery_csv" ]]; then health_recovery_csv+=","; fi
  health_recovery_csv+="$health_recovery"
  if [[ -n "$ui_recovery_csv" ]]; then ui_recovery_csv+=","; fi
  ui_recovery_csv+="$ui_recovery"

  unset health_ok_after ui_ok_after
done

python3 - "$OUTPUT" "$CYCLES" "$passed" "$failed" "$health_recovery_csv" "$ui_recovery_csv" <<'PY'
import json
import pathlib
import sys
import time

path = pathlib.Path(sys.argv[1]).expanduser()
cycles = int(sys.argv[2])
passed = int(sys.argv[3])
failed = int(sys.argv[4])
health_recoveries = [int(x) for x in sys.argv[5].split(",") if x]
ui_recoveries = [int(x) for x in sys.argv[6].split(",") if x]
payload = {
    "schema": "video-forge.samsung-bark.v1",
    "name": "Background App Resilience Kill",
    "timestamp_unix": int(time.time()),
    "kill_mode": "am_kill",
    "force_stop_used": False,
    "cycles": cycles,
    "passed": passed,
    "failed": failed,
    "fastapi_recovery_seconds": health_recoveries,
    "ui_foreground_recovery_seconds": ui_recoveries,
    "ok": failed == 0,
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
PY

if (( failed > 0 )); then
  echo "BARK_RED: $failed cycle(s) failed backend or kiosk-shell recovery" >&2
  exit 4
fi

echo "BARK_GREEN"
