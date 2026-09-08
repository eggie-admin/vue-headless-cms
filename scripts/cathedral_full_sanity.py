from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
read = lambda path: (ROOT / path).read_text(encoding="utf-8")
release = json.loads(read("release/version.json"))
pyproject = tomllib.loads(read("server/pyproject.toml"))
package = json.loads(read("apps/forge-ui/package.json"))
export_preset = read("godot/export_presets.cfg")
fdroid_metadata = read(f"fdroid/metadata/{release['packageId']}.yml")
server_main = read("server/app/main.py")
main_ts = read("apps/forge-ui/src/main.ts")
styles_css = read("apps/forge-ui/src/styles.css")
android_manifest = read("godot/android-plugin/plugin/src/main/AndroidManifest.xml")
webview_plugin = read("godot/android-plugin/plugin/src/main/java/art/eggiebagelface/cathedral/CathedralAndroidPlugin.kt")
widget_provider = read("godot/android-plugin/plugin/src/main/java/art/eggiebagelface/cathedral/CathedralWidgetProvider.kt")
network_security = read("godot/android-plugin/plugin/src/main/res/xml/cathedral_network_security.xml")

runtime_cdn_markers = ("cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com")
bootstrap_vendor = package.get("kai9000Vendor", {}).get("bootstrap", {})

checks = [
    ("single-python-control-plane", "FastAPI" in server_main),
    ("fastapi-release-identity", 'FastAPI(title="KAI 9000 Control", version=APP_VERSION)' in server_main),
    ("fastapi-health-version", '"version": APP_VERSION' in server_main),
    ("webview-cors-origin", "https://appassets.androidplatform.net" in server_main),
    ("vite-portable-base", "base: './'" in read("apps/forge-ui/vite.config.ts")),
    ("jquery-cockpit-render-owner", "kai9000Cockpit" in main_ts and "Save revision" in main_ts),
    ("jquery-pinned", package.get("dependencies", {}).get("jquery") == "4.0.0"),
    ("jquery-ui-pinned", package.get("dependencies", {}).get("jquery-ui") == "1.14.2"),
    ("bootstrap-vendor-pinned", bootstrap_vendor.get("version") == "5.3.8" and len(bootstrap_vendor.get("sha512", "")) == 128),
    ("no-runtime-cdn", not any(marker in main_ts or marker in styles_css for marker in runtime_cdn_markers)),
    ("typed-native-bridge", (ROOT / "apps/forge-ui/src/lib/cathedralBridge.ts").is_file()),
    ("godot-gradle-export", "gradle_build/use_gradle_build=true" in export_preset),
    ("godot-android-v2-plugin", "org.godotengine.plugin.v2" in android_manifest),
    ("private-widget-receiver", 'android:exported="false"' in android_manifest),
    ("webview-asset-loader", "WebViewAssetLoader" in webview_plugin),
    ("webview-file-access-denied", "allowFileAccess = false" in webview_plugin),
    ("webview-content-access-denied", "allowContentAccess = false" in webview_plugin),
    ("third-party-cookies-denied", "setAcceptThirdPartyCookies(view, false)" in webview_plugin),
    ("webview-debug-debugonly", "setWebContentsDebuggingEnabled(BuildConfig.DEBUG)" in webview_plugin),
    ("origin-locked-webmessage", "setOf(APP_ORIGIN)" in webview_plugin),
    ("cleartext-loopback-only", 'cleartextTrafficPermitted="false"' in network_security and "127.0.0.1" in network_security and "localhost" in network_security),
    ("androidx-webkit-pinned", "androidx.webkit:webkit:1.17.0" in read("godot/android-plugin/plugin/build.gradle.kts")),
    ("godot-aar-pinned", "org.godotengine:godot:4.7.2.stable" in read("godot/android-plugin/plugin/build.gradle.kts")),
    ("web-cms-node-wired", "WebCmsBridge" in read("godot/scenes/main.tscn")),
    ("persistent-cms-store", "CREATE TABLE IF NOT EXISTS cms_documents" in read("server/app/cms/store.py")),
    ("revision-conflict-gate", "CmsConflictError" in read("server/app/cms/store.py")),
    ("cms-write-token-gate", "X-Cathedral-Token" in server_main),
    ("cms-crud-api", "/api/cms/documents" in server_main),
    ("cms-runtime-manifest", "/api/cms/runtime-manifest" in server_main),
    ("godot-cms-registry", "CmsRegistry" in read("godot/scenes/main.tscn") and (ROOT / "godot/scripts/cms_registry.gd").is_file()),
    ("bridge-message-size-gate", "raw.length() > 32768" in read("godot/scripts/web_cms_bridge.gd")),
    ("widget-fixed-command-boundary", "CONTROL_SCRIPT" in widget_provider and "arrayOf(command)" in widget_provider and "Runtime.getRuntime().exec" not in widget_provider),
    ("widget-final-branding", "Video Forge" not in widget_provider),
    (
        "release-truth-file",
        set(release) == {"packageId", "version", "pythonVersion", "versionCode"}
        and release["packageId"].startswith("art.eggiebagelface.")
        and isinstance(release["versionCode"], int)
        and release["versionCode"] > 0,
    ),
    ("release-truth-godot", f'version/code={release["versionCode"]}' in export_preset and f'version/name="{release["version"]}"' in export_preset and f'package/unique_name="{release["packageId"]}"' in export_preset),
    ("release-truth-python", pyproject["project"]["version"] == release["pythonVersion"]),
    ("release-truth-fastapi", f'APP_VERSION = "{release["pythonVersion"]}"' in server_main),
    ("release-truth-fdroid", f'CurrentVersion: {release["version"]}' in fdroid_metadata and f'CurrentVersionCode: {release["versionCode"]}' in fdroid_metadata),
]

failures = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'} {name}")
print(f"{len(checks) - len(failures)}/{len(checks)} Cathedral full-mutation checks passed")
raise SystemExit(1 if failures else 0)
