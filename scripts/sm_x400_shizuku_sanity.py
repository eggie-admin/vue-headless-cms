#!/usr/bin/env python3
"""Validate the optional Samsung SM-X400 Shizuku privilege-broker contract."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "samsung-sm-x400" / "frontend" / "widget" / "shizuku" / "shizuku.manifest.json"


def load_manifest() -> dict[str, object]:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Shizuku manifest must be a JSON object")
    return value


def validate(value: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if value.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    if value.get("id") != "samsung-sm-x400.frontend.widget.shizuku":
        errors.append("unexpected Shizuku capability id")
    if value.get("optional") is not True:
        errors.append("Shizuku must remain optional")
    if value.get("preferredMode") != "wireless-adb":
        errors.append("preferredMode must remain wireless-adb for the Secure Folder target")

    secure = value.get("secureFolderTarget")
    if not isinstance(secure, dict):
        errors.append("secureFolderTarget is required")
    else:
        if secure.get("rootAllowed") is not False:
            errors.append("root must remain disabled for the trusted Secure Folder target")
        if secure.get("suiAllowed") is not False:
            errors.append("Sui must remain disabled for the trusted Secure Folder target")
        if secure.get("developerOptionsRequired") is not True:
            errors.append("Developer Options requirement must stay explicit")

    lab = value.get("rootedLabTarget")
    if not isinstance(lab, dict) or lab.get("secureFolderTrusted") is not False:
        errors.append("rooted lab target must never claim Secure Folder trust")

    deps = value.get("dependencyPolicy")
    if not isinstance(deps, dict):
        errors.append("dependencyPolicy is required")
    else:
        if deps.get("apkRequired") is not False:
            errors.append("Shizuku must not become a mandatory APK dependency")
        if deps.get("npmPackages") != []:
            errors.append("Shizuku broker must not add npm packages")
        if deps.get("pythonPackages") != []:
            errors.append("Shizuku broker sanity must not add Python packages")
        if deps.get("hiddenApiBypassRequired") is not False:
            errors.append("HiddenApiBypass must not be required by default")

    safety = value.get("safety")
    if not isinstance(safety, dict):
        errors.append("safety contract is required")
    else:
        for field in ("noArbitraryShellFromModels", "typedAllowlistedActionsOnly", "noSecretStorage", "noPublicListener"):
            if safety.get(field) is not True:
                errors.append(f"safety.{field} must remain true")
    return errors


def adb_report() -> dict[str, object]:
    adb = shutil.which("adb")
    if not adb:
        return {"adb": False, "connected": False}
    state = subprocess.run([adb, "get-state"], check=False, capture_output=True, text=True, timeout=5)
    connected = state.returncode == 0 and state.stdout.strip() == "device"
    report: dict[str, object] = {"adb": True, "connected": connected}
    if not connected:
        return report

    def shell(*args: str) -> str:
        result = subprocess.run([adb, "shell", *args], check=False, capture_output=True, text=True, timeout=8)
        return (result.stdout or result.stderr).strip()

    report.update({
        "model": shell("getprop", "ro.product.model"),
        "android": shell("getprop", "ro.build.version.release"),
        "developerOptions": shell("settings", "get", "global", "development_settings_enabled"),
        "adbEnabled": shell("settings", "get", "global", "adb_enabled"),
        "shizukuPackage": bool(shell("pm", "path", "moe.shizuku.privileged.api")),
    })
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", action="store_true", help="add read-only ADB device diagnostics")
    args = parser.parse_args()

    try:
        manifest = load_manifest()
        errors = validate(manifest)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1

    report: dict[str, object] = {
        "ok": not errors,
        "optional": True,
        "preferredMode": manifest.get("preferredMode"),
        "errors": errors,
    }
    if args.device:
        report["device"] = adb_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
