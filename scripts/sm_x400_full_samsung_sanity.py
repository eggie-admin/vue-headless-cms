#!/usr/bin/env python3
"""Validate the static Samsung SM-X400 multi-repository integration contract."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "samsung-sm-x400" / "samsung-dev-stack.manifest.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")

EXPECTED_PORTS = {
    "axs": 8767,
    "vnc": 5901,
    "websocket": 6080,
    "cockpit": 8787,
    "ollama": 11434,
}
EXPECTED_PACKAGES = {
    "termux": "com.termux",
    "termuxWidget": "com.termux.widget",
    "termuxApi": "com.termux.api",
    "shizuku": "moe.shizuku.privileged.api",
    "termuxX11": "com.termux.x11",
}
REQUIRED_REPOS = {
    "cathedral",
    "hydraShell",
    "shizuku",
    "termux",
    "termuxX11",
    "launcher",
    "fossCatalog",
}


def main() -> int:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors: list[str] = []

    if value.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    if value.get("id") != "hydra.samsung.sm-x400.full-stack":
        errors.append("unexpected manifest id")

    target = value.get("target", {})
    if target.get("manufacturer") != "Samsung" or target.get("model") != "SM-X400":
        errors.append("target must remain Samsung SM-X400")
    if target.get("android") != 16 or target.get("abi") != "arm64-v8a":
        errors.append("Android/ABI target drift")

    trust = value.get("trust", {})
    if trust.get("preferred") != "stock-shizuku":
        errors.append("preferred trust lane must remain stock-shizuku")
    secure = trust.get("secureFolder", {})
    if secure.get("rootAllowed") is not False or secure.get("suiAllowed") is not False:
        errors.append("Secure Folder lane must not allow root or Sui")
    if secure.get("developerOptions") is not True:
        errors.append("Developer Options requirement must stay explicit")
    lab = trust.get("rootedLab", {})
    if lab.get("secureFolderTrusted") is not False:
        errors.append("rooted lab must never claim Secure Folder trust")

    if value.get("packages") != EXPECTED_PACKAGES:
        errors.append("Android package contract drift")
    if value.get("loopbackPorts") != EXPECTED_PORTS:
        errors.append("loopback port contract drift")

    repos = value.get("repositories", {})
    if set(repos) != REQUIRED_REPOS:
        errors.append("repository constellation is incomplete")
    for name, record in repos.items():
        if not isinstance(record, dict):
            errors.append(f"repositories.{name} must be an object")
            continue
        if not record.get("repo") or not record.get("branch") or not record.get("role"):
            errors.append(f"repositories.{name} is missing repo/branch/role")
        head = record.get("head")
        if head is not None and (not isinstance(head, str) or not SHA40.fullmatch(head)):
            errors.append(f"repositories.{name}.head must be a 40-character SHA")

    security = value.get("security", {})
    required_true = (
        "loopbackOnly",
        "typedAllowlistedPrivilegedActions",
        "externalCapabilitiesRemainOptional",
    )
    for field in required_true:
        if security.get(field) is not True:
            errors.append(f"security.{field} must remain true")
    required_false = ("arbitraryModelShell", "automaticRoot", "secretsInSource")
    for field in required_false:
        if security.get(field) is not False:
            errors.append(f"security.{field} must remain false")

    print(json.dumps({
        "ok": not errors,
        "target": "Samsung SM-X400",
        "trustLane": trust.get("preferred"),
        "repositories": sorted(repos),
        "errors": errors,
    }, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
