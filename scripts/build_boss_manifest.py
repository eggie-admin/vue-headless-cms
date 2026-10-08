from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "boss-ai.manifest.json"
ENCODED = ROOT / "manifests" / "boss-ai.manifest.b64"


def canonical_bytes() -> bytes:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("secrets", {}).get("embed_values") is not False:
        raise SystemExit("manifest must forbid embedded secret values")
    return (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")


def expected_base64() -> str:
    return base64.b64encode(canonical_bytes()).decode("ascii") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    current = MANIFEST.read_bytes()
    canonical = canonical_bytes()
    if current != canonical:
        if args.check:
            raise SystemExit("boss manifest JSON is not canonical")
        MANIFEST.write_bytes(canonical)

    encoded = expected_base64()
    if args.check:
        if not ENCODED.is_file() or ENCODED.read_text(encoding="ascii") != encoded:
            raise SystemExit("boss manifest Base64 copy is stale")
        if base64.b64decode(encoded.strip(), validate=True) != canonical:
            raise SystemExit("boss manifest Base64 roundtrip failed")
        print("boss manifest canonical/base64 check green")
        return 0

    ENCODED.write_text(encoded, encoding="ascii")
    print(f"wrote {ENCODED.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
