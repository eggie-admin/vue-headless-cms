from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "infra/samsung/samsung-lite-profile.json"
QUALIFICATION = ROOT / "infra/samsung/samsung-device-qualification.yml"
BENCHMARK_CONFIG = ROOT / "infra/samsung/samsung-benchmark.yml"
MANIFEST = ROOT / "godot/android-plugin/plugin/src/main/AndroidManifest.xml"
WIDGET = ROOT / "godot/android-plugin/plugin/src/main/java/art/eggiebagelface/cathedral/CathedralWidgetProvider.kt"
PLUGIN = ROOT / "godot/android-plugin/plugin/src/main/java/art/eggiebagelface/cathedral/CathedralAndroidPlugin.kt"
GODOT_BRIDGE = ROOT / "godot/scripts/web_cms_bridge.gd"
CONTROL = ROOT / "termux/cathedral-control.sh"
INSTALLER = ROOT / "termux/install-samsung-edge.sh"
ADB_GUARD = ROOT / "scripts/samsung_background_guard_adb.sh"
ADB_SMOKE = ROOT / "scripts/samsung_device_smoke_adb.py"
BARK = ROOT / "scripts/samsung_bark_test.sh"
KIOSK = ROOT / "scripts/samsung_kiosk_adb.sh"
BENCH = ROOT / "scripts/samsung_benchmark.py"
PYPROJECT = ROOT / "server/pyproject.toml"
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
qualification = QUALIFICATION.read_text(encoding="utf-8")
benchmark_config = BENCHMARK_CONFIG.read_text(encoding="utf-8")
manifest = MANIFEST.read_text(encoding="utf-8")
widget = WIDGET.read_text(encoding="utf-8")
plugin = PLUGIN.read_text(encoding="utf-8")
godot_bridge = GODOT_BRIDGE.read_text(encoding="utf-8")
control = CONTROL.read_text(encoding="utf-8")
installer = INSTALLER.read_text(encoding="utf-8")
adb_guard = ADB_GUARD.read_text(encoding="utf-8")
adb_smoke = ADB_SMOKE.read_text(encoding="utf-8")
bark = BARK.read_text(encoding="utf-8")
kiosk = KIOSK.read_text(encoding="utf-8")
bench = BENCH.read_text(encoding="utf-8")
pyproject = PYPROJECT.read_text(encoding="utf-8")
godot = GODOT.read_text(encoding="utf-8")
package = json.loads(APPS_PACKAGE.read_text(encoding="utf-8"))
android_ci = ANDROID_CI.read_text(encoding="utf-8")
forge_ci = FORGE_CI.read_text(encoding="utf-8")

check(profile["devices"]["sm_x400"]["role"] == "interactive_dev_tablet", "SM-X400 role drift")
check(profile["devices"]["s10_lite"]["role"] == "headless_edge_node", "S10 Lite role drift")
check(profile["widget"]["blind_toggle"] is False and profile["widget"]["explicit_on_off"] is True, "widget must use explicit ON/OFF")
check("background_guard" in profile["widget"]["controls"], "widget background guard control missing")

check('android:name="com.termux.permission.RUN_COMMAND"' in manifest, "Termux RUN_COMMAND permission missing")
check('<package android:name="com.termux"' in manifest, "Termux package visibility query missing")
check("CathedralWidgetProvider" in manifest and "android.appwidget.action.APPWIDGET_UPDATE" in manifest, "widget receiver missing")
check("WRITE_SECURE_SETTINGS" not in manifest and "QUERY_ALL_PACKAGES" not in manifest, "privileged/broad Android permission present")

check("Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS" in widget and "Settings.Global" not in widget, "developer options baseline must open Settings only")
check("com.samsung.android.sm.ACTION_OPEN_CHECKABLE_LISTACTIVITY" in widget, "Samsung Never sleeping deeplink missing")
check('putExtra("activity_type", SAMSUNG_NEVER_SLEEPING)' in widget and "SAMSUNG_NEVER_SLEEPING = 2" in widget, "Samsung Never sleeping activity type drift")
check("Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS" in widget, "generic battery optimization fallback missing")
check("CONTROL_SCRIPT" in widget and "cathedral-control" in widget, "widget must call fixed control script")

check("DevicePolicyManager" in plugin, "managed kiosk must use Android device policy")
check("isLockTaskPermitted" in plugin and "startLockTask" in plugin and "stopLockTask" in plugin, "managed lock-task kiosk gate missing")
check("isManagedKioskPermitted" in plugin and "requestManagedKioskStart" in plugin, "Godot managed kiosk API missing")
check("android.kiosk.start" in godot_bridge and "android.kiosk.stop" in godot_bridge, "CMS managed kiosk bridge missing")
check("screen pinning" not in plugin.lower(), "native plugin must not silently fall back to screen pinning")

check('renderer/rendering_method="mobile"' in godot and 'renderer/rendering_method.mobile="mobile"' in godot, "Godot Mobile/Vulkan lane not enabled")
check(profile["termux"]["x11_autostart"] is False and profile["termux"]["vnc_autostart"] is False, "X11/VNC must stay on-demand")
check("termux-services" in installer and "allow-external-apps=true" in installer, "Termux widget installer incomplete")
check("termux-wake-lock" in control and "termux-wake-unlock" in control and "cathedral-wakelock" in control, "reversible Termux wake guard missing")
check("RELEASE_WAKE_LOCK_ON_STOP=true" in installer, "wake-lock stop policy must be explicit")
check("RUN_IN_BACKGROUND allow" in adb_guard and "RUN_ANY_IN_BACKGROUND allow" in adb_guard, "ADB background app-op recovery missing")
check("set-standby-bucket" in adb_guard and "active" in adb_guard, "ADB active standby bucket guard missing")
check("eval " not in control and "sh -c" not in control and "case \"${1:-status}\"" in control, "control script must remain allowlisted/no eval")

check("schema: video-forge.samsung-device-qualification.v1" in qualification, "qualification YAML schema missing")
check("public_network_targets: false" in qualification and "local_only: true" in qualification, "qualification must stay local-only")
check("kill_mode: am_kill" in qualification and "force_stop_forbidden: true" in qualification, "BARK kill policy drift")
check("preferred_mode: android_enterprise_lock_task" in qualification and "dpc_allowlist_required: true" in qualification, "managed kiosk policy drift")
check("unmanaged_fallback: immersive_shell_only" in qualification and "never_auto_enable_screen_pinning: true" in qualification, "unmanaged kiosk fallback drift")

check("SAMSUNG_DEVICE_SMOKE_GREEN" in adb_smoke and "adb" in adb_smoke.lower(), "physical ADB smoke runner missing")
check("RUN_IN_BACKGROUND" in adb_smoke and "standby_active" in adb_smoke, "physical smoke must inspect background guard")
check("vulkan_version" in adb_smoke and "webviewupdate" in adb_smoke and "fastapi_unhealthy" in adb_smoke, "physical smoke coverage drift")
check('"$ADB" shell am kill' in bark, "BARK must use ActivityManager background kill")
check('"$ADB" shell am force-stop' not in bark, "BARK must never force-stop packages")
check("BARK_GREEN" in bark and "app_foreground" in bark and "fastapi" in bark.lower(), "BARK backend/UI recovery proof missing")
check("dumpsys device_policy" in kiosk and "lock task" in kiosk.lower(), "kiosk device-policy diagnostic missing")

check("DEFAULT_CONFIG = ROOT / \"infra/samsung/samsung-benchmark.yml\"" in bench, "benchmark runner must load canonical YAML")
check("yaml.safe_load" in bench and "config_is_authoritative" in bench, "benchmark YAML validation missing")
check("http://127.0.0.1:8000/api/health" in benchmark_config and "http://127.0.0.1:11434/api/tags" in benchmark_config, "benchmark config must probe loopback services")
check("public_network_targets: false" in benchmark_config and "execute_model_output: false" in benchmark_config, "benchmark policy must remain local and non-agentic")
check('"PyYAML>=6.0.2,<7"' in pyproject, "PyYAML benchmark dependency missing")

scripts = package.get("scripts", {})
check(package.get("devDependencies", {}).get("prettier") == "3.6.2", "Prettier must be pinned")
check(scripts.get("samsung:guard:adb") == "bash ../scripts/samsung_background_guard_adb.sh", "npm Samsung guard helper missing")
check(scripts.get("samsung:smoke:adb") == "python3 ../scripts/samsung_device_smoke_adb.py", "npm physical smoke command missing")
check(scripts.get("samsung:bark") == "bash ../scripts/samsung_bark_test.sh", "npm BARK command missing")
check(scripts.get("samsung:kiosk:status") == "bash ../scripts/samsung_kiosk_adb.sh status", "npm kiosk status command missing")
check(scripts.get("samsung:qualify") == "npm run samsung:smoke && npm run samsung:bench", "npm local qualification chain missing")
check(scripts.get("samsung:qualify:device") == "npm run samsung:smoke:adb && npm run samsung:kiosk:status && npm run samsung:bark", "npm physical qualification chain missing")

check("samsung_edge_sanity.py" in forge_ci, "Forge CI Samsung gate missing")
check("CathedralWidgetProvider" in android_ci and "com.termux.permission.RUN_COMMAND" in android_ci, "APK verification must assert widget/Termux permission")

print(f"SAMSUNG_EDGE_SANITY_GREEN passes={passes}")
