from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
read = lambda path: (ROOT / path).read_text(encoding="utf-8")
release = json.loads(read("release/version.json"))
pyproject = tomllib.loads(read("server/pyproject.toml"))
export_preset = read("godot/export_presets.cfg")
fdroid_metadata = read("fdroid/metadata/art.eggiebagelface.videoforge.dev.yml")

checks = [
    ("single-python-control-plane", "FastAPI" in read("server/app/main.py")),
    ("webview-cors-origin", "https://appassets.androidplatform.net" in read("server/app/main.py")),
    ("vite-portable-base", "base: './'" in read("apps/forge-ui/vite.config.ts")),
    ("typed-native-bridge", (ROOT / "apps/forge-ui/src/lib/cathedralBridge.ts").is_file()),
    ("godot-gradle-export", "gradle_build/use_gradle_build=true" in export_preset),
    ("godot-android-v2-plugin", "org.godotengine.plugin.v2" in read("godot/android-plugin/plugin/src/main/AndroidManifest.xml")),
    ("webview-asset-loader", "WebViewAssetLoader" in read("godot/android-plugin/plugin/src/main/java/art/eggiebagelface/cathedral/CathedralAndroidPlugin.kt")),
    ("origin-locked-webmessage", "setOf(APP_ORIGIN)" in read("godot/android-plugin/plugin/src/main/java/art/eggiebagelface/cathedral/CathedralAndroidPlugin.kt")),
    ("cleartext-loopback-only", "127.0.0.1" in read("godot/android-plugin/plugin/src/main/res/xml/cathedral_network_security.xml")),
    ("androidx-webkit-pinned", "androidx.webkit:webkit:1.17.0" in read("godot/android-plugin/plugin/build.gradle.kts")),
    ("godot-aar-pinned", "org.godotengine:godot:4.7.2.stable" in read("godot/android-plugin/plugin/build.gradle.kts")),
    ("web-cms-node-wired", "WebCmsBridge" in read("godot/scenes/main.tscn")),
    ("persistent-cms-store", "CREATE TABLE IF NOT EXISTS cms_documents" in read("server/app/cms/store.py")),
    ("revision-conflict-gate", "CmsConflictError" in read("server/app/cms/store.py")),
    ("cms-write-token-gate", "X-Cathedral-Token" in read("server/app/main.py")),
    ("cms-crud-api", "/api/cms/documents" in read("server/app/main.py")),
    ("cms-runtime-manifest", "/api/cms/runtime-manifest" in read("server/app/main.py")),
    ("vue-json-editor", "Save revision" in read("apps/forge-ui/src/App.vue")),
    ("godot-cms-registry", "CmsRegistry" in read("godot/scenes/main.tscn") and (ROOT / "godot/scripts/cms_registry.gd").is_file()),
    ("bridge-message-size-gate", "raw.length() > 32768" in read("godot/scripts/web_cms_bridge.gd")),
    ("release-truth-file", release == {"packageId": "art.eggiebagelface.videoforge.dev", "version": "0.6.0-dev", "pythonVersion": "0.6.0", "versionCode": 6}),
    ("release-truth-godot", f'version/code={release["versionCode"]}' in export_preset and f'version/name="{release["version"]}"' in export_preset and f'package/unique_name="{release["packageId"]}"' in export_preset),
    ("release-truth-python", pyproject["project"]["version"] == release["pythonVersion"]),
    ("release-truth-fdroid", f'CurrentVersion: {release["version"]}' in fdroid_metadata and f'CurrentVersionCode: {release["versionCode"]}' in fdroid_metadata),
]

failures = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'} {name}")
print(f"{len(checks) - len(failures)}/{len(checks)} Cathedral full-mutation checks passed")
raise SystemExit(1 if failures else 0)
