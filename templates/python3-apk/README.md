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
- `requirements-build.txt`: host Python build graph aligned to p4a `2026.5.9`, including its declared build dependencies and the upstream-compatible `Cython==0.29.36` pin.
- `requirements-app.txt`: Python packages intended to exist inside the Android application. Keep this aligned with `.p4a`.
- `.p4a`: canonical p4a APK configuration.

Do not add Android runtime packages to `requirements-build.txt`. Do not add host-only build tools to `.p4a`.

For p4a `2026.5.9`, do not casually upgrade Cython to 3.x or wheel beyond p4a's `wheel~=0.43.0` constraint. Those are part of the cross-compile compatibility contract, not ordinary desktop dependency freshness targets.

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
python -m pip check
python -c 'import Cython, appdirs, build, colorama, jinja2, packaging, setuptools, sh, toml, wheel; print("PY_BUILD_DEPS_GREEN")'
command -v meson
command -v ninja
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
2. Host Python build requirements resolve, pass `pip check`, and import successfully.
3. SDK/NDK binaries resolve from the canonical SDK root.
4. Static Python and `.p4a` sanity checks pass.
5. p4a cross-compilation succeeds.
6. APK package id and `arm64-v8a` payload are verified with `aapt`.
7. APK, SHA-256, build inputs and badging report upload as workflow artifacts.

## Candidate and nightly lanes

Development changes stage on `samsung-sm-x400-build-candidate`. The regular workflow supports manual and branch/PR builds. The nightly workflow is defined separately and is intended to build the candidate ref without merging it automatically.

GitHub scheduled workflows execute from the repository default branch. Therefore the nightly workflow becomes autonomous only after its workflow definition is present on `main`. Until then it remains a staged validation path.
