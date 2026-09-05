# Samsung SM-X400 Python APK Forge

This template builds a Python 3 WebView control APK for the Samsung SM-X400 lane with python-for-android (p4a).

## Build contract

- Host CI: Ubuntu 24.04
- Host Python: 3.14
- Java: Temurin/OpenJDK 17
- Android target API: 36
- Android NDK API: 29
- Android NDK: r28c (`28.2.13676358`)
- ABI: `arm64-v8a`
- Bootstrap: `webview`
- Package: `art.eggiebagelface.samsungx400.python`
- App port: `8765`

## Dependency files

- `apt-build-dependencies.txt`: Ubuntu/host compiler and p4a prerequisites.
- `requirements-build.txt`: host Python build tools. This includes p4a, Cython, wheel/build tooling and virtualenv.
- `requirements-app.txt`: Python packages intended to exist inside the Android application. Keep this aligned with `.p4a`.
- `.p4a`: canonical p4a APK configuration.

Do not add Android runtime packages to `requirements-build.txt`. Do not add host-only build tools to `.p4a`.

## Canonical Android SDK paths

Use one SDK root and derive every binary from it:

```bash
export ANDROIDSDK="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-$HOME/Android/Sdk}}"
export ANDROID_SDK_ROOT="$ANDROIDSDK"
export ANDROID_HOME="$ANDROIDSDK"
export ANDROIDNDK="$ANDROIDSDK/ndk/28.2.13676358"
export ANDROID_NDK_HOME="$ANDROIDNDK"
export ANDROIDAPI=36
export NDKAPI=29

SDKMANAGER="$ANDROIDSDK/cmdline-tools/latest/bin/sdkmanager"
ADB="$ANDROIDSDK/platform-tools/adb"
AAPT="$ANDROIDSDK/build-tools/36.0.0/aapt"
```

Avoid adding the entire SDK tree to `PATH`. If interactive shell convenience is needed, add only these directories:

```bash
export PATH="$ANDROIDSDK/cmdline-tools/latest/bin:$ANDROIDSDK/platform-tools:$ANDROIDSDK/build-tools/36.0.0:$PATH"
```

## Ubuntu host install

```bash
sudo apt-get update
mapfile -t APT_DEPS < <(grep -Ev '^\s*(#|$)' apt-build-dependencies.txt)
sudo apt-get install -y --no-install-recommends "${APT_DEPS[@]}"

python -m pip install --upgrade pip
python -m pip install --requirement requirements-build.txt
python -c 'import Cython, build, packaging, setuptools, wheel, virtualenv; print("PY_BUILD_DEPS_GREEN")'
p4a --version
```

## SDK/NDK install

```bash
SDKMANAGER="$ANDROIDSDK/cmdline-tools/latest/bin/sdkmanager"
yes | "$SDKMANAGER" --licenses >/dev/null || true
"$SDKMANAGER" \
  platform-tools \
  'platforms;android-36' \
  'build-tools;36.0.0' \
  'ndk;28.2.13676358'
```

## Build

```bash
export BUILD_MODE=debug
./build-apk.sh
```

Expected artifact:

```text
dist/samsung-sm-x400-python-debug.apk
```

`build-apk.sh` also writes `dist/sha256.txt` and runs `sanity.py` against the APK.

## CI gates

A build is not GREEN until all of these pass:

1. Host APT prerequisites installed.
2. Host Python build requirements import successfully.
3. SDK/NDK binaries resolve from the canonical SDK root.
4. Static Python and `.p4a` sanity checks pass.
5. p4a cross-compilation succeeds.
6. APK package id and `arm64-v8a` payload are verified with `aapt`.
7. APK, SHA-256, build inputs and badging report upload as workflow artifacts.

## Candidate and nightly lanes

Development changes stage on `samsung-sm-x400-build-candidate`. The regular workflow supports manual and branch/PR builds. The nightly workflow is defined separately and is intended to build the candidate ref without merging it automatically.

GitHub scheduled workflows execute from the repository default branch. Therefore the nightly workflow becomes autonomous only after its workflow definition is present on `main`. Until then, use its `workflow_dispatch` path for candidate validation.
