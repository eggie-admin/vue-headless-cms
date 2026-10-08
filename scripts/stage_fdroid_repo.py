from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage a private F-Droid binary repository input bundle.")
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--package", default="art.eggiebagelface.videoforge.dev")
    parser.add_argument("--version-code", default="4")
    args = parser.parse_args()

    apk = args.apk.resolve()
    if not apk.is_file() or apk.suffix.lower() != ".apk":
        raise SystemExit(f"APK not found: {apk}")

    root = args.output.resolve()
    repo = root / "repo"
    metadata = root / "metadata"
    repo.mkdir(parents=True, exist_ok=True)
    metadata.mkdir(parents=True, exist_ok=True)

    staged_apk = repo / f"{args.package}_{args.version_code}.apk"
    shutil.copy2(apk, staged_apk)

    source_metadata = Path("fdroid/metadata") / f"{args.package}.yml"
    if not source_metadata.is_file():
        raise SystemExit(f"Missing private F-Droid metadata: {source_metadata}")
    shutil.copy2(source_metadata, metadata / source_metadata.name)

    digest = sha256(staged_apk)
    (root / "SHA256SUMS").write_text(f"{digest}  repo/{staged_apk.name}\n", encoding="utf-8")
    (root / "README.txt").write_text(
        "PRIVATE F-DROID STAGING BUNDLE\n"
        "This is not a signed F-Droid repository yet.\n"
        "Run fdroid init/update on a trusted host with a persistent repo signing key.\n"
        "Do not commit the repo keystore or passwords.\n",
        encoding="utf-8",
    )

    print(f"staged={staged_apk}")
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
