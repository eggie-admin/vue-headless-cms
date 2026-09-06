#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACT="$ROOT/ai/runtime-contract.json"
SOURCE_LOCK="$ROOT/ai/drive-source-of-truth.json"

python3 - "$CONTRACT" "$SOURCE_LOCK" <<'PY'
import json, sys
contract_path, lock_path = sys.argv[1:3]
d = json.load(open(contract_path, encoding="utf-8"))
lock = json.load(open(lock_path, encoding="utf-8"))

assert d["runtime"]["api_base"] == "http://127.0.0.1:8797/api/ai"
assert d["runtime"]["ollama"] == "http://127.0.0.1:11434"
assert d["policy"]["no_runtime_duplication"] is True
assert d["policy"]["no_public_bind"] is True
assert d["policy"]["no_model_shell"] is True
assert d["policy"]["google_drive_is_authoritative"] is True
assert d["policy"]["github_staging_is_mirror"] is True
assert d["policy"]["apk_build_owner"] == "GitHub Actions after CAST ULTIMA"

assert d["source_of_truth"]["provider"] == "Google Drive"
assert d["source_of_truth"]["payload_file_id"] == lock["payload"]["file_id"]
assert d["source_of_truth"]["payload_sha256"] == lock["payload"]["sha256"]
assert d["source_of_truth"]["seal_file_id"] == lock["seal"]["file_id"]
assert d["source_of_truth"]["seal_sha256"] == lock["seal"]["sha256"]
assert lock["build_gate"]["locked"] is True
assert lock["build_gate"]["unlock_phrase"] == "CAST ULTIMA"
assert lock["build_gate"]["apk_build_allowed"] is False

print("KAI_SAMSUNG_AI_DRIVE_SOURCE_GREEN")
PY
