from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

checks = [
    ("single-python-control-plane", "FastAPI" in (ROOT / "server/app/main.py").read_text()),
    ("webview-cors-origin", "https://appassets.androidplatform.net" in (ROOT / "server/app/main.py").read_text()),
    ("vite-portable-base", "base: './'" in (ROOT / "apps/forge-ui/vite.config.ts").read_text()),
    ("typed-native-bridge", (ROOT / "apps/forge-ui/src/lib/cathedralBridge.ts").is_file()),
    ("godot-gradle-export", "gradle_build/use_gradle_build=true" in (ROOT / "godot/export_presets.cfg").read_text()),
    ("godot-android-v2-plugin", "org.godotengine.plugin.v2" in (ROOT / "godot/android-plugin/plugin/src/main/AndroidManifest.xml").read_text()),
    ("webview-asset-loader", "WebViewAssetLoader" in (ROOT / "godot/android-plugin/plugin/src/main/java/art/eggiebagelface/cathedral/CathedralAndroidPlugin.kt").read_text()),
    ("origin-locked-webmessage", "setOf(APP_ORIGIN)" in (ROOT / "godot/android-plugin/plugin/src/main/java/art/eggiebagelface/cathedral/CathedralAndroidPlugin.kt").read_text()),
    ("cleartext-loopback-only", "127.0.0.1" in (ROOT / "godot/android-plugin/plugin/src/main/res/xml/cathedral_network_security.xml").read_text()),
    ("androidx-webkit-pinned", "androidx.webkit:webkit:1.17.0" in (ROOT / "godot/android-plugin/plugin/build.gradle.kts").read_text()),
    ("godot-aar-pinned", "org.godotengine:godot:4.7.2.stable" in (ROOT / "godot/android-plugin/plugin/build.gradle.kts").read_text()),
    ("web-cms-node-wired", "WebCmsBridge" in (ROOT / "godot/scenes/main.tscn").read_text()),
]

failures = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'} {name}")
print(f"{len(checks) - len(failures)}/{len(checks)} Cathedral full-automation checks passed")
raise SystemExit(1 if failures else 0)
