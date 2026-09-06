#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def jread(path: str):
    return json.loads(read(path))


checks: list[tuple[str, bool, str]] = []

def check(name: str, ok: bool, detail: str) -> None:
    checks.append((name, ok, detail))

version = jread("release/version.json")
check("product-name", version.get("productName") == "Luhm OS", str(version.get("productName")))
check("working-title", version.get("workingTitle") == "KAI 9000", str(version.get("workingTitle")))
check("package-id", version.get("packageId") == "art.eggiebagelface.videoforge.dev", str(version.get("packageId")))
check("version", version.get("version") == "0.7.0-dev" and version.get("versionCode") == 7, f"{version.get('version')} ({version.get('versionCode')})")

apps = jread("apps/package.json")
ui = jread("apps/forge-ui/package.json")
check("npm-boss", apps.get("packageManager") == "npm@12.0.2", str(apps.get("packageManager")))
check("workspace-root", apps.get("name") == "luhm-os-web-workspace", str(apps.get("name")))
check("workspace-ui", ui.get("name") == "luhm-os-ui", str(ui.get("name")))
check("workspace-script", "--workspace=luhm-os-ui" in str(apps.get("scripts", {}).get("build", "")), str(apps.get("scripts", {}).get("build")))

lock = ROOT / "apps/package-lock.json"
lock_ok = False
lock_detail = "missing"
if lock.is_file() and lock.stat().st_size > 0:
    try:
        lock_doc = json.loads(lock.read_text(encoding="utf-8"))
        lock_ok = lock_doc.get("lockfileVersion") == 3
        lock_detail = f"lockfileVersion={lock_doc.get('lockfileVersion')}"
    except Exception as exc:
        lock_detail = f"invalid: {type(exc).__name__}"
check("committed-npm-lock", lock_ok, lock_detail)

pyproject = read("server/pyproject.toml")
check("python-control-name", 'name = "luhm-os-control"' in pyproject, "server/pyproject.toml")
check("python-control-version", 'version = "0.7.0"' in pyproject, "server/pyproject.toml")

preset = read("godot/export_presets.cfg")
check("godot-product", 'package/name="Luhm OS"' in preset, "godot/export_presets.cfg")
check("godot-version", 'version/code=7' in preset and 'version/name="0.7.0-dev"' in preset, "godot/export_presets.cfg")
check("godot-package-id", 'package/unique_name="art.eggiebagelface.videoforge.dev"' in preset, "godot/export_presets.cfg")
check("arm64-only", 'architectures/arm64-v8a=true' in preset and all(x in preset for x in ['architectures/armeabi-v7a=false','architectures/x86=false','architectures/x86_64=false']), "godot/export_presets.cfg")

metadata = read("fdroid/metadata/art.eggiebagelface.videoforge.dev.yml")
check("fdroid-brand", re.search(r"(?m)^Name: Luhm OS$", metadata) is not None, "fdroid metadata")
check("fdroid-version", re.search(r"(?m)^CurrentVersion: 0\.7\.0-dev$", metadata) is not None and re.search(r"(?m)^CurrentVersionCode: 7$", metadata) is not None, "fdroid metadata")

proxy_wf = read(".github/workflows/luhm-fdroid-private-proxy.yml")
release_wf = read(".github/workflows/luhm-os-ultima-release.yml")
check("proxy-manual-only", "workflow_dispatch:" in proxy_wf and "\n  push:" not in proxy_wf and "\n  pull_request:" not in proxy_wf, "proxy workflow")
check("release-manual-only", "workflow_dispatch:" in release_wf and "\n  push:" not in release_wf and "\n  pull_request:" not in release_wf, "release workflow")
check("ultima-phrase-gate", "inputs.authorization_phrase == 'CAST ULTIMA'" in release_wf, "release workflow")
check("proxy-source-sha", "source_sha" in proxy_wf and "SOURCE_SHA" in proxy_wf, "proxy workflow")
check("no-final-autopublish", "publish:" in proxy_wf and "default: false" in proxy_wf, "proxy workflow")

bad = [item for item in checks if not item[1]]
for name, ok, detail in checks:
    print(("PASS" if ok else "FAIL"), name, "::", detail)
print(f"LUHM_PRE_ULTIMA_GATE {len(checks)-len(bad)}/{len(checks)}")
if bad:
    print("ULTIMA_FAILED_SOURCE_GATE")
    raise SystemExit(1)
print("ULTIMA_SOURCE_GREEN")
