from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: sanity.py APK")

    apk = Path(sys.argv[1])
    if not apk.is_file() or apk.stat().st_size < 1_000_000:
        raise SystemExit("APK_SANITY_FAIL: missing or implausibly small APK")

    digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()

    required = [
        "AndroidManifest.xml",
        "classes.dex",
    ]
    for item in required:
        if item not in names:
            raise SystemExit(f"APK_SANITY_FAIL: missing {item}")

    if not any(name.startswith("lib/arm64-v8a/") for name in names):
        raise SystemExit("APK_SANITY_FAIL: arm64-v8a native payload missing")

    if not any("libpython" in name.lower() for name in names):
        raise SystemExit("APK_SANITY_FAIL: embedded Python runtime missing")

    forbidden_fragments = (
        ".env",
        "credentials.json",
        "service-account",
        "id_rsa",
        ".pem",
        ".key",
    )
    bad = [name for name in names if any(fragment in name.lower() for fragment in forbidden_fragments)]
    if bad:
        raise SystemExit(f"APK_SANITY_FAIL: forbidden secret-like files packaged: {bad[:5]}")

    print(f"APK_SANITY_GREEN bytes={apk.stat().st_size} sha256={digest} entries={len(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
