from __future__ import annotations

import base64
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
manifest_path = ROOT / "manifests/boss-ai.manifest.json"
encoded_path = ROOT / "manifests/boss-ai.manifest.b64"
providers = (ROOT / "server/app/boss/providers.py").read_text()
feeds = (ROOT / "server/app/boss/feeds.py").read_text()
service = (ROOT / "server/app/boss/service.py").read_text()
workflow = (ROOT / ".github/workflows/forge-ci.yml").read_text()
boss_test_path = ROOT / "tests/test_boss_pipeline.py"

manifest_bytes = manifest_path.read_bytes()
manifest = json.loads(manifest_bytes)
encoded = "".join(encoded_path.read_text().split())

checks = [
    ("boss01-canonical-id", manifest.get("id") == "videoForge.bossAi"),
    ("boss02-no-secrets", manifest["secrets"]["embed_values"] is False),
    ("boss03-base64-roundtrip", base64.b64decode(encoded, validate=True) == manifest_bytes),
    ("boss04-three-ai-adapters", set(manifest["providers"]) == {"openai", "ollama", "gemini"}),
    ("boss05-operator-feed-allowlist", "BOSS_FEEDS_JSON" in feeds and "source_id" in feeds),
    ("boss06-https-feed-boundary", 'parsed.scheme != "https"' in feeds),
    ("boss07-untrusted-feed-prompt", "<untrusted_feed_item>" in providers and "Never follow instructions" in providers),
    ("boss08-auto-fanout-off", 'os.getenv("BOSS_AUTO_FANOUT", "")' in providers),
    ("boss09-sqlite-dedupe", "INSERT OR IGNORE INTO boss_feed_seen" in feeds),
    ("boss10-ci-gate", "boss_ai_sanity.py" in workflow and boss_test_path.is_file()),
]
failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print("PASS" if ok else "FAIL", name)
if failed:
    print("RED", ", ".join(failed), file=sys.stderr)
    raise SystemExit(1)
print("GREEN 10/10 boss AI passes")
