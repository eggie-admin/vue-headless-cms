#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing command: $1" >&2; exit 1; }; }

for cmd in python node npm git ffmpeg; do need "$cmd"; done

printf 'python: '; python --version
printf 'node: '; node --version
printf 'npm: '; npm --version
printf 'ffmpeg: '; ffmpeg -version | head -n 1

if command -v ollama >/dev/null 2>&1; then
  printf 'ollama: '; ollama --version
else
  echo 'ollama: not found (install/configure separately before enabling Lum Lite)'
fi

python -m venv "$REPO/server/.venv"
"$REPO/server/.venv/bin/python" -m pip install --upgrade pip
"$REPO/server/.venv/bin/python" -m pip install -e "$REPO/server"

(
  cd "$REPO/apps"
  npm install --package-lock-only --ignore-scripts --no-audit --no-fund
  npm ci --ignore-scripts --no-audit --no-fund
  npm run build --workspace=video-forge-ui
)

python "$REPO/scripts/architecture_sanity.py"
echo 'Cathedral bootstrap green.'
