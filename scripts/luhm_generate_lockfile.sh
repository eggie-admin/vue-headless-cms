#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/apps"

NODE="$(node --version 2>/dev/null || true)"
NPM="$(npm --version 2>/dev/null || true)"

echo "node=$NODE"
echo "npm=$NPM"

[[ "$NODE" =~ ^v24\. ]] || {
  echo 'LUHM_LOCK_FAILED: Node 24.x required; target is 24.18.x.' >&2
  exit 41
}
[[ "$NPM" =~ ^12\.0\.2$ ]] || {
  echo 'LUHM_LOCK_FAILED: npm 12.0.2 required. npm is boss, so lock generation must use the release npm.' >&2
  exit 42
}

rm -f package-lock.json
npm install --package-lock-only --ignore-scripts --no-audit --no-fund
python3 - <<'PY'
import json
from pathlib import Path
p=Path('package-lock.json')
d=json.loads(p.read_text())
assert d.get('lockfileVersion') == 3, d.get('lockfileVersion')
assert d.get('name') == 'luhm-os-web-workspace', d.get('name')
print('LOCKFILE_SCHEMA_GREEN')
PY

npm ci --ignore-scripts --no-audit --no-fund
npm run build --workspace=luhm-os-ui
test -s forge-ui/dist/index.html

git diff --check -- package-lock.json
sha256sum package-lock.json

echo 'LUHM_LOCK_GREEN'
echo 'Review apps/package-lock.json, then commit it to luhm-os-ultima. This script never commits, pushes, builds an APK, or triggers GitHub Actions.'
