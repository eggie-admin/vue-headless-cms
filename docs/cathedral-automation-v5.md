# Video Forge Cathedral Automation v5

Status target: CODE / WEBVIEW / GODOT / PYTHON / APK / PRIVATE F-DROID GREEN.

## Runtime law

- Python 3.14 + FastAPI remains the single edge control plane on Termux.
- Ollama remains loopback-only at 127.0.0.1:11434.
- Godot 4.7.2 owns the native scene, avatar, windows and cutscenes.
- Vue/Vite owns the CMS surface.
- Android WebView embeds the built Vue bundle from app assets.
- The WebView native bridge accepts messages only from `https://appassets.androidplatform.net`.
- The packaged CMS may reach cleartext HTTP only on loopback for the edge-dev FastAPI API.
- Models never receive arbitrary shell or Android package-manager authority.

## Automated build

1. Node 24 + npm 12 builds `apps/forge-ui`.
2. CI copies `dist/` into the Android plugin assets tree.
3. Gradle builds the `CathedralAndroid` v2 plugin AAR against Godot 4.7.2.
4. CI stages the plugin under `godot/addons/CathedralAndroid`.
5. Godot installs its Android Gradle build template and exports the arm64 debug APK.
6. CI verifies APK signature, 16 KiB alignment, ABI, plugin metadata and packaged CMS assets.
7. CI stages the private F-Droid repository input bundle.

PR/nightly builds use an ephemeral debug key. Stable signing stays a separate approval-gated release concern.
