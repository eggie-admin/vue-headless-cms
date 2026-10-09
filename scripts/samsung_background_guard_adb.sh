#!/usr/bin/env bash
set -euo pipefail

ADB="${ADB:-adb}"
PACKAGES=(
  "com.termux"
  "art.eggiebagelface.videoforge.dev"
)

command -v "$ADB" >/dev/null 2>&1 || {
  echo "adb not found: $ADB" >&2
  exit 1
}

"$ADB" get-state >/dev/null

for package in "${PACKAGES[@]}"; do
  echo "Applying Android background guard to $package"
  "$ADB" shell cmd appops set "$package" RUN_IN_BACKGROUND allow
  "$ADB" shell cmd appops set "$package" RUN_ANY_IN_BACKGROUND allow
  "$ADB" shell am set-standby-bucket "$package" active
  printf 'standby bucket %s: ' "$package"
  "$ADB" shell am get-standby-bucket "$package" || true
done

cat <<'EOF'
ANDROID_BACKGROUND_GUARD_GREEN

Android app-ops and standby buckets are permissive for the Cathedral packages.
Samsung's OEM Sleeping/Deep sleeping/Never sleeping list is a separate policy layer.
On Samsung, press the widget GUARD button once and add Termux + Video Forge Cathedral
under Never sleeping apps. Knox/device-owner automation can manage that OEM layer on
fully managed devices.
EOF
