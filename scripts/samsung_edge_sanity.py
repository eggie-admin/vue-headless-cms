from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "infra/samsung/samsung-lite-profile.json"
UNIVERSAL = ROOT / "release/samsung-universal-arm64.json"
MANIFEST = ROOT / "godot/android-plugin/plugin/src/main/AndroidManifest.xml"
WIDGET = ROOT / "godot/android-plugin/plugin/src/main/java/art/eggiebagelface/cathedral/CathedralWidgetProvider.kt"
PLUGIN = ROOT / "godot/android-plugin/plugin/src/main/java/art/eggiebagelface/cathedral/CathedralAndroidPlugin.kt"
EXPORT = ROOT / "godot/export_presets.cfg"
GODOT = ROOT / "godot/project.godot"
APPS_PACKAGE = ROOT / "apps/package.json"
ANDROID_CI = ROOT / ".github/workflows/android-apk.yml"
FORGE_CI = ROOT / ".github/workflows/forge-ci.yml"

passes = 0


def check(condition: bool, message: str) -> None:
    global passes
    if not condition:
        raise SystemExit(f"SAMSUNG_EDGE_SANITY_FAIL: {message}")
    passes += 1


profile = json.loads(PROFILE.read_text(encoding="utf-8"))
universal = json.loads(UNIVERSAL.read_text(encoding="utf-8"))
manifest = MANIFEST.read_text(encoding="utf-8")
widget = WIDGET.read_text(encoding="utf-8")
plugin = PLUGIN.read_text(encoding="utf-8")
export = EXPORT.read_text(encoding="utf-8")
godot = GODOT.read_text(encoding="utf-8")
package = json.loads(APPS_PACKAGE.read_text(encoding="utf-8"))
android_ci = ANDROID_CI.read_text(encoding="utf-8")
forge_ci = FORGE_CI.read_text(encoding="utf-8")

devices = profile["devices"]
check(profile["profile_version"] == "2.0.0", "Samsung stock profile version drift")
check(profile["doctrine"] == "universal_stock_standalone", "Samsung stock doctrine drift")
check(profile["application"]["package_id"] == "art.eggiebagelface.luhmos", "package identity drift")
check(profile["application"]["abi"] == "arm64-v8a", "Samsung ABI drift")
check(profile["application"]["min_sdk"] == 24 and profile["application"]["target_sdk"] == 36, "SDK contract drift")
check(profile["application"]["root_required"] is False, "stock Samsung lane must remain unrooted")
check(profile["application"]["external_daemon_required"] is False, "external daemon became mandatory")

check(devices["s24_fe"]["model_pattern"] == "SM-S721*", "S24 FE model pattern drift")
check(devices["s24_fe"]["role"] == "primary_phone_and_secure_folder_client", "S24 FE role drift")
check(devices["sm_x400"]["model_pattern"] == "SM-X400", "SM-X400 model drift")
check(devices["sm_x400"]["role"] == "stock_tablet_testing", "SM-X400 role drift")
check(devices["s10_lite"]["model_pattern"] == "SM-G770*", "S10 Lite model pattern drift")
check(devices["s10_lite"]["role"] == "stock_compatibility_phone", "S10 Lite role drift")

secure = profile["secure_folder"]
check(secure["role"] == "protected_cockpit_client", "Secure Folder role drift")
check(secure["same_signed_apk"] is True and secure["separate_profile_data"] is True, "Secure Folder package/data boundary drift")
check(secure["cross_profile_silent_install"] is False, "cross-profile silent install must stay disabled")
check(secure["build_forge_inside_profile"] is False and secure["signing_keys_inside_profile"] is False, "Secure Folder must not become forge/signing authority")

distribution = profile["distribution"]
check(distribution["bootstrap"].startswith("https://github.com/eggie-admin/hydra-shell-android/releases/"), "trusted release bootstrap drift")
check(distribution["android_user_confirmation_required"] is True, "Android install confirmation must remain required")
check(distribution["request_install_packages_permission"] is False, "broad package install permission must remain disabled")
check(distribution["same_signer_update_required"] is True, "same-signer update continuity must remain required")

check("com.termux.permission.RUN_COMMAND" not in manifest, "production manifest still requests Termux RUN_COMMAND")
check('<package android:name="com.termux"' not in manifest, "production manifest still queries Termux")
check("CathedralWidgetProvider" in manifest and "android.appwidget.action.APPWIDGET_UPDATE" in manifest, "widget receiver missing")
check('android:exported="false"' in manifest, "widget receiver must remain private")
check("WRITE_SECURE_SETTINGS" not in manifest and "QUERY_ALL_PACKAGES" not in manifest, "privileged/broad Android permission present")
check("REQUEST_INSTALL_PACKAGES" not in manifest, "bootstrap lane must not request package installer authority")

check("Runtime.getRuntime().exec" not in widget and "com.termux" not in widget, "widget regained shell/Termux authority")
check("openCathedral(context)" in widget and "Android manages LuHm OS app lifecycle" in widget, "widget must use local Android lifecycle")
check("Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS" in widget and "Settings.Global" not in widget, "developer options baseline must open Settings only")
check("com.samsung.android.sm.ACTION_OPEN_CHECKABLE_LISTACTIVITY" in widget, "Samsung Never sleeping deeplink missing")
check('putExtra("activity_type", SAMSUNG_NEVER_SLEEPING)' in widget and "SAMSUNG_NEVER_SLEEPING = 2" in widget, "Samsung Never sleeping activity type drift")
check("Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS" in widget, "generic battery optimization fallback missing")

check("setImmersiveKiosk" in plugin and "deviceSnapshot" in plugin, "native kiosk/device hooks missing")
check('put("external_runtime_required", false)' in plugin, "device snapshot must report standalone runtime")
check("MIXED_CONTENT_NEVER_ALLOW" in plugin and "setAcceptCookie(false)" in plugin, "WebView hardening drift")
check('renderer/rendering_method="mobile"' in godot and 'renderer/rendering_method.mobile="mobile"' in godot, "Godot Mobile/Vulkan lane not enabled")
check('gradle_build/min_sdk="24"' in export and 'gradle_build/target_sdk="36"' in export, "Godot Samsung SDK export drift")
check("architectures/arm64-v8a=true" in export and "architectures/armeabi-v7a=false" in export, "Godot Samsung ABI export drift")

check(universal["application"]["package_id"] == profile["application"]["package_id"], "universal manifest package mismatch")
check(universal["application"]["min_sdk"] == profile["application"]["min_sdk"], "universal manifest min SDK mismatch")
check(universal["application"]["target_sdk"] == profile["application"]["target_sdk"], "universal manifest target SDK mismatch")
check({"SM-S721*", "SM-X400", "SM-G770*"}.issubset({d["model_pattern"] for d in universal["samsung_device_families"]}), "universal Samsung device matrix incomplete")

check(package.get("devDependencies", {}).get("prettier") == "3.6.2", "Prettier must remain pinned")
check("samsung_edge_sanity.py" in forge_ci, "Forge CI Samsung gate missing")
check("samsung_edge_sanity.py" in android_ci, "Android CI Samsung gate missing")
check("Standalone Samsung APK must not request Termux RUN_COMMAND" in android_ci, "Android CI must reject obsolete Termux permission")
check("Bootstrap install portal must not request package-installer authority" in android_ci, "Android CI must reject broad install authority")

print(f"SAMSUNG_EDGE_SANITY_GREEN passes={passes}")
