#!/usr/bin/env python3
"""Fail-closed Crown Gate audit for the stock LuHm OS Samsung lane."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def data(path: str) -> dict:
    return json.loads(text(path))


def require(ok: bool, message: str) -> None:
    if not ok:
        raise AssertionError(message)


def pass_identity() -> None:
    version = data("release/version.json")
    universal = data("release/samsung-universal-arm64.json")
    export = text("godot/export_presets.cfg")
    require(version["packageId"] == "art.eggiebagelface.luhmos", "canonical package id drifted")
    require(universal["application"]["package_id"] == version["packageId"], "release package mismatch")
    require('package/unique_name="art.eggiebagelface.luhmos"' in export, "Godot package mismatch")


def pass_stock_unrooted() -> None:
    crown = data("release/crown-install-lane.json")
    manifest = text("godot/android-plugin/plugin/src/main/AndroidManifest.xml")
    require(crown["root_of_trust"]["device_root_required"] is False, "device root must stay off")
    require(crown["root_of_trust"]["root_install"] is False, "root install must stay off")
    require("REQUEST_INSTALL_PACKAGES" not in manifest, "package installer permission entered app manifest")
    require("com.termux.permission.RUN_COMMAND" not in manifest, "Termux RUN_COMMAND entered app manifest")


def pass_webview_boundary() -> None:
    kotlin = text("godot/android-plugin/plugin/src/main/java/art/eggiebagelface/cathedral/CathedralAndroidPlugin.kt")
    network = text("godot/android-plugin/plugin/src/main/res/xml/cathedral_network_security.xml")
    for needle in (
        "MIXED_CONTENT_NEVER_ALLOW",
        "allowFileAccess = false",
        "allowContentAccess = false",
        "setAcceptCookie(false)",
        "setAcceptThirdPartyCookies(view, false)",
        'APP_ORIGIN = "https://appassets.androidplatform.net"',
    ):
        require(needle in kotlin, f"WebView invariant missing: {needle}")
    require('<base-config cleartextTrafficPermitted="false"' in network, "global cleartext denial missing")


def pass_arcade_capability_isolation() -> None:
    host = text("apps/forge-ui/src/cathedralArcade.ts")
    arcade = text("apps/forge-ui/public/arcade/index.html")
    bootstrap = text("apps/forge-ui/src/bootstrap.ts")
    manifest = data("release/cathedral-arcade.json")

    require('sandbox="allow-scripts"' in host, "Arcade iframe must grant scripts only")
    require("allow-same-origin" not in host, "Arcade must keep an opaque origin")
    require("event.source !== frame.contentWindow" in host, "save adapter must source-lock child messages")
    require("sanitizeState(record.state)" in host, "parent must schema-limit Arcade save writes")
    require("cathedralBridge" not in host and "postNative" not in host, "Arcade host gained native bridge access")
    require("connect-src 'none'" in arcade, "Arcade CSP must deny network connections")
    require("CathedralBridge" not in arcade and "sessionStorage" not in arcade, "Arcade child references privileged cockpit capability")
    require("Cathedral Arcade unavailable; privileged cockpit remains online." in bootstrap, "optional Arcade failure must fail open")
    require(manifest["runtime_isolation"]["allow_same_origin"] is False, "Arcade isolation manifest drift")
    require(manifest["runtime_isolation"]["native_bridge_visible"] is False, "Arcade bridge boundary drift")


def pass_provenance() -> None:
    workflow = text(".github/workflows/android-apk.yml")
    arcade = data("release/cathedral-arcade.json")
    for needle in ("GODOT_EDITOR_SHA256", "GODOT_TEMPLATES_SHA256", "NPM_LOCK_SHA256", "sha256sum --check --strict"):
        require(needle in workflow, f"build provenance gate missing: {needle}")
    require("persist-credentials: false" in workflow, "checkout credentials must not persist")
    for source in arcade["creative_sources"]:
        commit = str(source.get("commit", ""))
        require(bool(re.fullmatch(r"[0-9a-f]{40}", commit)), f"mutable/unpinned Arcade provenance: {source.get('repository')}")
        require("branch" not in source, f"Arcade provenance must not rely on mutable branch: {source.get('repository')}")


def pass_signing_and_artifacts() -> None:
    workflow = text(".github/workflows/android-apk.yml")
    universal = data("release/samsung-universal-arm64.json")
    for needle in ("apksigner", "zipalign", "sha256sum", "lib/arm64-v8a/", "assets/cms/index.html"):
        require(needle in workflow, f"artifact evidence missing: {needle}")
    require(universal["application"]["persistent_release_signer_required"] is True, "release signer continuity not required")
    require("ephemeral-ci" in workflow, "debug/release signing separation evidence missing")


def pass_lum_crown_authority() -> None:
    crown = data("release/crown-install-lane.json")
    require(crown["authority"]["visible_operational_crown"] == "Lum", "Lum does not hold visible crown")
    require(crown["authority"]["human_final_authority"] == "Professor", "human final authority drifted")
    require(crown["promotion"]["fail_closed"] is True, "promotion must fail closed")
    require(crown["promotion"]["automatic_merge"] is False, "automatic merge is forbidden")


def pass_play_first_keyless_cloud() -> None:
    crown = data("release/crown-install-lane.json")
    primary = crown["distribution"]["primary"]
    require(primary["channel"] == "google_play_internal", "Play internal must be primary")
    require(primary["unknown_sources_required"] is False, "Play path must not require unknown sources")
    require(crown["google_cloud"]["github_auth"] == "oidc_workload_identity_federation", "keyless WIF contract missing")
    require(crown["google_cloud"]["long_lived_service_account_json"] is False, "long-lived Google key forbidden")


def pass_play_bundle_and_wizard() -> None:
    export = text("godot/export_presets.cfg")
    wizard = text("apps/forge-ui/public/install/index.html")
    crown_ui = text("apps/forge-ui/src/crownMode.ts")
    require('name="Android Play Internal"' in export, "Play AAB preset missing")
    require("gradle_build/export_format=1" in export, "Play preset must export AAB")
    require("play.google.com/store/apps/details?id=art.eggiebagelface.luhmos" in wizard, "Play install action missing")
    require("hydra-shell-android/releases/latest" in wizard, "truthful signed APK fallback missing")
    require("Android may ask for confirmation" in wizard, "fallback confirmation disclosure missing")
    require('href="./install/"' in crown_ui, "Crown Gate must use packaged-appassets-relative install path")


def pass_hands_off_ci_contract() -> None:
    workflow = text(".github/workflows/crown-10pass.yml")
    copilot = text(".github/copilot-instructions.md")
    crown_ui = text("apps/forge-ui/src/crownMode.ts")
    require("python scripts/luhmos_crown_10pass.py" in workflow, "Crown workflow does not run 10-pass audit")
    require("python scripts/cathedral_full_sanity.py" in workflow, "Cathedral sanity missing from Crown workflow")
    require("npm run build --workspace=video-forge-ui" in workflow, "cockpit build missing from Crown workflow")
    require("forge-ui/dist/arcade/index.html" in workflow, "isolated Arcade artifact is not asserted by CI")
    require("CI evidence outranks agent confidence" in copilot, "Copilot evidence doctrine missing")
    require("LUM HOLDS THE CROWN" in crown_ui, "Crown UX missing")


PASSES = [
    ("01 identity", pass_identity),
    ("02 stock-unrooted boundary", pass_stock_unrooted),
    ("03 WebView/network boundary", pass_webview_boundary),
    ("04 Arcade capability isolation", pass_arcade_capability_isolation),
    ("05 immutable provenance", pass_provenance),
    ("06 signer/artifact evidence", pass_signing_and_artifacts),
    ("07 Lum crown authority", pass_lum_crown_authority),
    ("08 Play-first keyless cloud", pass_play_first_keyless_cloud),
    ("09 Play bundle + click wizard", pass_play_bundle_and_wizard),
    ("10 hands-off CI contract", pass_hands_off_ci_contract),
]


def main() -> int:
    failures: list[str] = []
    for name, check in PASSES:
        try:
            check()
            print(f"[GREEN] {name}")
        except Exception as exc:
            failures.append(f"{name}: {exc}")
            print(f"[RED]   {name}: {exc}")
    if failures:
        print("CROWN_GATE_RED")
        return 1
    print("LUM_HOLDS_THE_CROWN_GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
