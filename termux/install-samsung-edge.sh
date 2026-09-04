#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
KAI_HOME="${KAI_HOME:-$HOME/kai9000}"
ENABLE_WIDGET=false
AUTOSTART=false

for arg in "$@"; do
  case "$arg" in
    --enable-widget-control) ENABLE_WIDGET=true ;;
    --autostart) AUTOSTART=true ;;
    *) echo "unknown argument: $arg" >&2; exit 64 ;;
  esac
done

command -v pkg >/dev/null 2>&1 || { echo 'Termux pkg command required.' >&2; exit 1; }
command -v curl >/dev/null 2>&1 || pkg install -y curl
command -v sv >/dev/null 2>&1 || pkg install -y termux-services

mkdir -p "$KAI_HOME/bin" "$KAI_HOME/config" "$KAI_HOME/state" "$KAI_HOME/logs"
install -m 700 "$REPO/termux/cathedral-control.sh" "$KAI_HOME/bin/cathedral-control"
printf 'VIDEO_FORGE_REPO=%q\n' "$REPO" >"$KAI_HOME/config/widget.env"
chmod 600 "$KAI_HOME/config/widget.env"

SERVICE_DIR="$PREFIX/var/service/video-forge-cathedral"
mkdir -p "$SERVICE_DIR/log" "$KAI_HOME/logs/runit-cathedral"
cat >"$SERVICE_DIR/run" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec "$REPO/termux/run-cathedral.sh"
EOF
chmod 700 "$SERVICE_DIR/run"
cat >"$SERVICE_DIR/log/run" <<EOF
#!/data/data/com.termux/files/usr/bin/sh
exec svlogd -tt "$KAI_HOME/logs/runit-cathedral"
EOF
chmod 700 "$SERVICE_DIR/log/run"
touch "$SERVICE_DIR/down"

if $ENABLE_WIDGET; then
  PROP_DIR="$HOME/.termux"
  PROP_FILE="$PROP_DIR/termux.properties"
  mkdir -p "$PROP_DIR"
  touch "$PROP_FILE"
  if grep -q '^allow-external-apps=' "$PROP_FILE"; then
    sed -i 's/^allow-external-apps=.*/allow-external-apps=true/' "$PROP_FILE"
  else
    printf '\nallow-external-apps=true\n' >>"$PROP_FILE"
  fi
  command -v termux-reload-settings >/dev/null 2>&1 && termux-reload-settings || true
fi

if $AUTOSTART; then
  BOOT_DIR="$HOME/.termux/boot"
  mkdir -p "$BOOT_DIR"
  cat >"$BOOT_DIR/video-forge-cathedral" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock >/dev/null 2>&1 || true
exec "$KAI_HOME/bin/cathedral-control" start
EOF
  chmod 700 "$BOOT_DIR/video-forge-cathedral"
fi

cat <<EOF
Samsung edge install complete.

Control script:
  $KAI_HOME/bin/cathedral-control

Runit service:
  $SERVICE_DIR

Widget setup requires BOTH:
  1. --enable-widget-control (allow-external-apps=true)
  2. Android Settings -> Apps -> Video Forge Cathedral -> Permissions -> Additional permissions -> Run commands in Termux environment

Autostart requires Termux:Boot to execute:
  $HOME/.termux/boot/video-forge-cathedral

X11/VNC are intentionally not started by this lite profile.
EOF
