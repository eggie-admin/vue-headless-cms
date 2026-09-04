#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

KAI_HOME="${KAI_HOME:-$HOME/kai9000}"
STATE_DIR="$KAI_HOME/state"
LOG_DIR="$KAI_HOME/logs"
CONFIG="$KAI_HOME/config/widget.env"
mkdir -p "$STATE_DIR" "$LOG_DIR"

if [[ -r "$CONFIG" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG"
fi

REPO="${VIDEO_FORGE_REPO:-$HOME/kai9000-forge}"
RUN_SCRIPT="$REPO/termux/run-cathedral.sh"
SERVICE_DIR="$PREFIX/var/service/video-forge-cathedral"
PORT="${VIDEO_FORGE_PORT:-8000}"
HEALTH_URL="http://127.0.0.1:${PORT}/api/health"
PID_FILE="$STATE_DIR/cathedral.pid"

require_run_script() {
  [[ -x "$RUN_SCRIPT" ]] || {
    echo "missing executable: $RUN_SCRIPT" >&2
    exit 2
  }
}

health() {
  curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1
}

start_fallback() {
  if health; then
    echo 'cathedral already online'
    return 0
  fi
  nohup "$RUN_SCRIPT" >>"$LOG_DIR/cathedral-fallback.log" 2>&1 &
  echo "$!" >"$PID_FILE"
}

start_service() {
  require_run_script
  command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock >/dev/null 2>&1 || true
  if health; then
    echo 'cathedral already online'
    return 0
  fi
  if command -v sv >/dev/null 2>&1 && [[ -d "$SERVICE_DIR" ]]; then
    if sv -w 3 up "$SERVICE_DIR" >/dev/null 2>&1; then
      sleep 0.8
      health && { echo 'cathedral online via runit'; return 0; }
    fi
  fi
  start_fallback
  sleep 1
  health && echo 'cathedral online via fallback' || { echo 'cathedral failed to start' >&2; exit 1; }
}

stop_service() {
  if command -v sv >/dev/null 2>&1 && [[ -d "$SERVICE_DIR" ]]; then
    sv -w 3 down "$SERVICE_DIR" >/dev/null 2>&1 || true
  fi
  if [[ -r "$PID_FILE" ]]; then
    pid="$(cat "$PID_FILE")"
    if [[ "$pid" =~ ^[0-9]+$ ]]; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
    rm -f "$PID_FILE"
  fi
  sleep 0.5
  if health; then
    echo 'cathedral still responding' >&2
    exit 1
  fi
  echo 'cathedral offline'
}

status_service() {
  if health; then
    printf '{"ok":true,"state":"online","health":"%s"}\n' "$HEALTH_URL"
  else
    printf '{"ok":true,"state":"offline","health":"%s"}\n' "$HEALTH_URL"
  fi
}

run_smoke() {
  require_run_script
  "$REPO/server/.venv/bin/python" "$REPO/scripts/samsung_benchmark.py" \
    --smoke \
    --output "$STATE_DIR/samsung-smoke.json"
}

run_benchmark() {
  require_run_script
  "$REPO/server/.venv/bin/python" "$REPO/scripts/samsung_benchmark.py" \
    --full \
    --output "$STATE_DIR/samsung-benchmark.json"
}

case "${1:-status}" in
  start) start_service ;;
  stop) stop_service ;;
  restart) stop_service || true; start_service ;;
  status) status_service ;;
  smoke) run_smoke ;;
  benchmark) run_benchmark ;;
  *)
    echo 'usage: cathedral-control {start|stop|restart|status|smoke|benchmark}' >&2
    exit 64
    ;;
esac
