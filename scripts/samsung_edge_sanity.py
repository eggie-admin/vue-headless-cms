from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "infra/samsung/samsung-lite-profile.json"
MANIFEST = ROOT / "godot/android-plugin/plugin/src/main/AndroidManifest.xml"
WIDGET = ROOT / "godot/android-plugin/plugin/src/main/java/art/eggiebagelface/cathedral/CathedralWidgetProvider.kt"
PLUGIN = ROOT / "godot/android-plugin/plugin/src/main/java/art/eggiebagelface/cathedral/CathedralAndroidPlugin.kt"
CONTROL = ROOT / "termux/cathedral-control.sh"
INSTALLER = ROOT / "termux/install-samsung-edge.sh"
ADB_GUARD = ROOT / "scripts/samsung_background_guard_adb.sh"
BENCH = ROOT / "scripts/samsung_benchmark.py"
BENCH_CONFIG = ROOT / "infra/samsung/samsung-benchmark.yml"
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
manifest = MANIFEST.read_text(encoding="utf-8")
widget = WIDGET.read_text(encoding="utf-8")
plugin = PLUGIN.read_text(encoding="utf-8")
control = CONTROL.read_text(encoding="utf-8")
installer = INSTALLER.read_text(encoding="utf-8")
adb_guard = ADB_GUARD.read_text(encoding="utf-8")
bench = BENCH.read_text(encoding="utf-8")
bench_config = BENCH_CONFIG.read_text(encoding="utf-8")
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
check("setImmersiveKiosk" in plugin and "deviceSnapshot" in plugin, "native kiosk/device hooks missing")
check('renderer/rendering_method="mobile"' in godot and 'renderer/rendering_method.mobile="mobile"' in godot, "Godot Mobile/Vulkan lane not enabled")
check(profile["termux"]["x11_autostart"] is False and profile["termux"]["vnc_autostart"] is False, "X11/VNC must stay on-demand")
check("termux-services" in installer and "allow-external-apps=true" in installer, "Termux widget installer incomplete")
check("termux-wake-lock" in control and "termux-wake-unlock" in control and "cathedral-wakelock" in control, "reversible Termux wake guard missing")
check("RELEASE_WAKE_LOCK_ON_STOP=true" in installer, "wake-lock stop policy must be explicit")
check("RUN_IN_BACKGROUND allow" in adb_guard and "RUN_ANY_IN_BACKGROUND allow" in adb_guard, "ADB background app-op recovery missing")
check("set-standby-bucket" in adb_guard and "active" in adb_guard, "ADB active standby bucket guard missing")
check("eval " not in control and "sh -c" not in control and "case \"${1:-status}\"" in control, "control script must remain allowlisted/no eval")
check("DEFAULT_CONFIG" in bench and "samsung-benchmark.yml" in bench, "benchmark runner must load canonical YAML config")
check("http://127.0.0.1:8000/api/health" in bench_config and "http://127.0.0.1:11434/api/tags" in bench_config, "benchmark YAML must probe loopback services")
check("public_network_targets: false" in bench_config, "benchmark YAML must forbid public network targets")
check(package.get("devDependencies", {}).get("prettier") == "3.6.2", "Prettier must be pinned")
check(package.get("scripts", {}).get("samsung:guard:adb") == "bash ../scripts/samsung_background_guard_adb.sh", "npm Samsung guard helper missing")
check("samsung_edge_sanity.py" in forge_ci, "Forge CI Samsung gate missing")
check("CathedralWidgetProvider" in android_ci and "com.termux.permission.RUN_COMMAND" in android_ci, "APK verification must assert widget/Termux permission")

print(f"SAMSUNG_EDGE_SANITY_GREEN passes={passes}")
