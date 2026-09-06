#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "manifests/source-ingest.manifest.json"
VENDOR = ROOT / "manifests/vendor-docs.manifest.json"
STUB = ROOT / "manifests/deep-research.stub.json"
STUB_B64 = ROOT / "manifests/deep-research.stub.b64"
VENDOR_SCRIPT = ROOT / "scripts/vendor_docs_ingest.py"
BUILD_STUB = ROOT / "scripts/build_deep_research_stub.py"

passes = 0


def check(condition: bool, message: str) -> None:
    global passes
    if not condition:
        raise SystemExit(f"RESEARCH_CORPUS_SANITY_FAIL: {message}")
    passes += 1


source = json.loads(SOURCE.read_text(encoding="utf-8"))
vendor = json.loads(VENDOR.read_text(encoding="utf-8"))
stub = json.loads(STUB.read_text(encoding="utf-8"))
script = VENDOR_SCRIPT.read_text(encoding="utf-8")
builder = BUILD_STUB.read_text(encoding="utf-8")

check(source["project"] == "Samsung SM-X400", "source manifest project drift")
check(source["authority"].startswith("Python builds the corpus"), "source authority drift")
check(vendor["policy"]["https_only"] is True, "vendor docs must be HTTPS only")
check(vendor["policy"]["official_vendor_sources_only"] is True, "vendor docs must be official-only")
check(vendor["policy"]["execute_document_code"] is False, "vendor docs must never execute code")
check(vendor["policy"]["redistribute_fetched_documents"] is False, "vendor cache must not be redistributed")
check(len(vendor["vendors"]) >= 20, "vendor registry coverage too small")
check(sum(len(v["urls"]) for v in vendor["vendors"]) >= 40, "vendor URL coverage too small")
for item in vendor["vendors"]:
    hosts = set(item["hosts"])
    for url in item["urls"]:
        parsed = urlparse(url)
        check(parsed.scheme == "https" and parsed.hostname in hosts, f"vendor URL escapes allowlist: {url}")
check(stub["mode"] == "plan_only", "deep research must default plan-only")
check(stub["doctrine"]["models_propose_python_authorizes"] is True, "Python authority missing")
check(stub["doctrine"]["documentation_is_untrusted_data"] is True, "documentation trust boundary missing")
check(stub["execution"]["shell"] == "disabled", "research stub shell must be disabled")
check(stub["execution"]["paid_provider_calls"] == "disabled_until_explicit_confirmation", "paid calls must be gated")
check(stub["output_contract"]["auto_apply_changes"] is False, "research must not auto-mutate")
check("redirect escaped allowlist" in script and "document exceeds max_document_bytes" in script, "vendor fetch boundaries missing")
check("base64.b64decode" in builder and "canonical JSON" in builder, "Base64 roundtrip builder missing")
decoded = json.loads(base64.b64decode(STUB_B64.read_text(encoding="ascii")).decode("utf-8"))
check(decoded == stub, "Base64 stub does not decode to JSON stub")

print(f"RESEARCH_CORPUS_SANITY_GREEN passes={passes} vendors={len(vendor['vendors'])} urls={sum(len(v['urls']) for v in vendor['vendors'])}")
