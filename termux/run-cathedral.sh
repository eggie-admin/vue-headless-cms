#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
PY="$REPO/server/.venv/bin/python"

if [[ ! -x "$PY" ]]; then
  echo 'Run termux/bootstrap-cathedral.sh first.' >&2
  exit 1
fi

export OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
export OPENAI_AGENT_MODEL="${OPENAI_AGENT_MODEL:-gpt-5.6-sol}"

if command -v ollama >/dev/null 2>&1 && ! curl -fsS "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
  echo 'Ollama is installed but not responding. Start it separately with: ollama serve' >&2
fi

exec "$PY" -m uvicorn app.main:app \
  --app-dir "$REPO/server" \
  --host 127.0.0.1 \
  --port "${VIDEO_FORGE_PORT:-8000}"
