# Samsung SM-X400 Python3 APK Forge

Reusable, arm64-first Python Android build template for the Samsung SM-X400 project.

## Doctrine

- `python-for-android==2026.5.9` is pinned for reproducible packaging.
- Android API 36 + NDK r28c are the canonical compiler lane.
- WebView bootstrap keeps the sample small and maps cleanly to the existing kiosk architecture.
- Python binds only to `127.0.0.1:8765` inside the APK.
- No provider credentials, API keys, signing secrets, or model weights belong in this template.
- PyTorch/Lightning/Forge stay in a separate GPU-worker environment, not inside the control APK.

## Local Linux build

Install the prerequisites listed by the current python-for-android documentation, then expose your SDK/NDK paths:

```bash
export ANDROIDSDK="$HOME/Android/Sdk"
export ANDROIDNDK="$ANDROIDSDK/ndk/28.2.13676358"
export ANDROIDAPI=36
export NDKAPI=29

cd templates/python3-apk
python3 -m venv .venv
source .venv/bin/activate
make install
make doctor
make build
```

Output:

```text
dist/samsung-sm-x400-python-debug.apk
dist/sha256.txt
```

## GitHub build

Workflow: `.github/workflows/python3-apk-template.yml`

It installs the Linux compiler prerequisites, Java 17, Android API 36, NDK r28c, pinned python-for-android, cross-compiles the APK, validates package/ABI identity, hashes it, and uploads the APK as a GitHub Actions artifact.

## Customize

Edit `.p4a` for package/name/version/requirements. Keep the arm64-only Samsung baseline unless another ABI is deliberately required.
