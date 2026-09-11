#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
PY="$REPO/server/.venv/bin/python"

if [[ ! -x "$PY" ]]; then
  echo 'Run termux/bootstrap-cathedral.sh first.' >&2
  exit 1
fi

mkdir -p "$REPO/state"
export OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
export OPENAI_AGENT_MODEL="${OPENAI_AGENT_MODEL:-gpt-5.6-sol}"
export GEMINI_MODEL="${GEMINI_MODEL:-gemini-3.7-flash}"
export BOSS_STATE_DB="${BOSS_STATE_DB:-$REPO/state/boss.sqlite3}"
export BOSS_AUTO_FANOUT="${BOSS_AUTO_FANOUT:-false}"
export GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
export GOOGLE_VEO_MODEL="${GOOGLE_VEO_MODEL:-veo-3.1-generate-001}"
export GOOGLE_DRIVE_MODE="${GOOGLE_DRIVE_MODE:-drive_file}"

if command -v ollama >/dev/null 2>&1 && ! curl -fsS "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
  echo 'Ollama is installed but not responding. Start it separately with: ollama serve' >&2
fi

exec "$PY" -m uvicorn app.main:app \
  --app-dir "$REPO/server" \
  --host 127.0.0.1 \
  --port "${VIDEO_FORGE_PORT:-8000}"
