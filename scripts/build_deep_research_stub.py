#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "manifests/deep-research.stub.json"
B64_PATH = ROOT / "manifests/deep-research.stub.b64"


def canonical_bytes() -> bytes:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def expected_b64() -> str:
    return base64.b64encode(canonical_bytes()).decode("ascii") + "\n"


def check() -> None:
    expected = expected_b64()
    actual = B64_PATH.read_text(encoding="ascii")
    if actual != expected:
        raise SystemExit("DEEP_RESEARCH_STUB_FAIL: Base64 transport does not match canonical JSON")
    decoded = base64.b64decode(actual).decode("utf-8")
    if json.loads(decoded) != json.loads(JSON_PATH.read_text(encoding="utf-8")):
        raise SystemExit("DEEP_RESEARCH_STUB_FAIL: decoded JSON mismatch")
    digest = hashlib.sha256(canonical_bytes()).hexdigest()
    print(f"DEEP_RESEARCH_STUB_GREEN sha256={digest}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check()
        return
    B64_PATH.write_text(expected_b64(), encoding="ascii", newline="\n")
    check()


if __name__ == "__main__":
    main()
