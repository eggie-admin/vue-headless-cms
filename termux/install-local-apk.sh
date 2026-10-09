#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

APK="${1:-$HOME/storage/downloads/video-forge-cathedral-debug.apk}"

if [[ ! -f "$APK" ]]; then
  echo "APK not found: $APK" >&2
  exit 2
fi

case "$APK" in
  *.apk) ;;
  *)
    echo "Refusing non-APK path: $APK" >&2
    exit 2
    ;;
esac

echo "=== VIDEO FORGE SAMSUNG LOCAL INSTALL ==="
sha256sum "$APK"
echo
echo "Samsung gate: Auto Blocker must allow this install."
echo "Android gate: Termux must be allowed under Install unknown apps."
echo

am start \
  -a android.settings.MANAGE_UNKNOWN_APP_SOURCES \
  -d 'package:com.termux' >/dev/null 2>&1 || true

echo "After granting Termux install permission, return here and open the APK."
termux-open "$APK"
