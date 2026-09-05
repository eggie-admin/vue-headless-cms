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

## Local `android` recipe override

`p4a-recipes/android/` is a local [python-for-android recipe](https://python-for-android.readthedocs.io/en/latest/recipes/) that shadows the bundled `android` recipe (p4a reads `./p4a-recipes` by default from this directory). It is byte-identical to the recipe shipped in the pinned `python-for-android==2026.5.9`, except for one additive fix:

- `src/pyproject.toml` declares `Cython>=0.29,<3.1` in `[build-system].requires`.

The bundled recipe's `src/setup.py` imports `Cython` at module scope, but ships no `pyproject.toml`, so p4a's isolated `python -m build --wheel` fell back to installing only `setuptools` and failed with `ModuleNotFoundError: No module named 'Cython'`. Declaring Cython as a build requirement lets the isolated build environment install it. This mirrors the upstream fix (kivy/python-for-android#3301) and can be dropped once a released p4a carries it.
