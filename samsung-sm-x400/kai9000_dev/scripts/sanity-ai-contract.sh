#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACT="$ROOT/ai/runtime-contract.json"

python3 - "$CONTRACT" <<'PY'
import json, sys
p=sys.argv[1]
d=json.load(open(p, encoding="utf-8"))
assert d["runtime"]["api_base"] == "http://127.0.0.1:8797/api/ai"
assert d["runtime"]["ollama"] == "http://127.0.0.1:11434"
assert d["policy"]["no_runtime_duplication"] is True
assert d["policy"]["no_public_bind"] is True
assert d["policy"]["no_model_shell"] is True
assert d["policy"]["apk_build_owner"] == "GitHub Actions after CAST ULTIMA"
print("KAI_SAMSUNG_AI_CONTRACT_GREEN")
PY
