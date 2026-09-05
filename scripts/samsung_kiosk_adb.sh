#!/usr/bin/env bash
set -euo pipefail

ADB="${ADB:-adb}"
APP_PACKAGE="${VIDEO_FORGE_PACKAGE:-art.eggiebagelface.videoforge.dev}"
TERMUX_PACKAGE="${TERMUX_PACKAGE:-com.termux}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACTION="${1:-status}"

command -v "$ADB" >/dev/null 2>&1 || { echo "adb not found: $ADB" >&2; exit 2; }
"$ADB" get-state >/dev/null

status() {
  echo "=== DEVICE ==="
  "$ADB" shell getprop ro.product.manufacturer | tr -d '\r'
  "$ADB" shell getprop ro.product.model | tr -d '\r'
  "$ADB" shell getprop ro.build.version.release | tr -d '\r'

  echo "=== PACKAGES ==="
  "$ADB" shell pm path "$APP_PACKAGE" || true
  "$ADB" shell pm path "$TERMUX_PACKAGE" || true

  echo "=== BACKGROUND GUARD ==="
  for package in "$TERMUX_PACKAGE" "$APP_PACKAGE"; do
    printf '%s standby: ' "$package"
    "$ADB" shell am get-standby-bucket "$package" 2>/dev/null | tr -d '\r' || true
    "$ADB" shell cmd appops get "$package" RUN_IN_BACKGROUND 2>/dev/null | tr -d '\r' || true
    "$ADB" shell cmd appops get "$package" RUN_ANY_IN_BACKGROUND 2>/dev/null | tr -d '\r' || true
  done

  echo "=== DEVICE POLICY / LOCK TASK ==="
  "$ADB" shell dumpsys device_policy 2>/dev/null | grep -E -i 'device owner|profile owner|lock task|locktask' | head -n 80 || true
  "$ADB" shell dumpsys activity activities 2>/dev/null | grep -E -i 'locktask|mLockTask|LockTask' | head -n 40 || true

  cat <<'EOF'
KIOSK_POLICY:
- Real kiosk = Android lock-task mode.
- Video Forge only starts managed lock-task when DevicePolicyManager reports the package allowlisted.
- On unmanaged devices, use the existing immersive shell only; do not silently fall back to screen pinning.
- Samsung Never sleeping apps is a separate OEM background policy and remains required unless managed policy replaces it.
EOF
}

case "$ACTION" in
  status)
    status
    ;;
  guard)
    bash "$ROOT/scripts/samsung_background_guard_adb.sh"
    status
    ;;
  launch)
    bash "$ROOT/scripts/samsung_background_guard_adb.sh" >/dev/null
    "$ADB" shell monkey -p "$APP_PACKAGE" -c android.intent.category.LAUNCHER 1 >/dev/null
    sleep 1
    status
    ;;
  *)
    echo "usage: $0 {status|guard|launch}" >&2
    exit 2
    ;;
esac
