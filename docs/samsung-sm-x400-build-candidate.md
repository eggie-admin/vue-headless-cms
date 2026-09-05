# Samsung SM-X400 APK Build Candidate

Branch: `samsung-sm-x400-build-candidate`

Purpose: stage and prove the Python/WebView APK forge before changes enter `samsung-sm-x400-backend` and before PR #3 can be considered for promotion.

## Dependency planes

### 1. Ubuntu host packages

Canonical file: `templates/python3-apk/apt-build-dependencies.txt`

This contains the compiler/autotools/JDK-adjacent host packages required by the python-for-android lane. CI reads the file directly.

### 2. Host Python build tools

Canonical file: `templates/python3-apk/requirements-build.txt`

This contains the pinned `python-for-android` release plus explicit Cython, wheel/build, packaging, setuptools and virtualenv tooling. These packages exist to build Android Python dependencies; they are not app payload requirements.

### 3. Android app Python packages

Canonical file: `templates/python3-apk/requirements-app.txt`

The non-p4a runtime packages in this file must remain aligned with `.p4a`. The p4a-provided `python3` runtime stays in `.p4a` and does not appear as a pip package in `requirements-app.txt`.

## Android SDK layout

One SDK root is authoritative:

```text
ANDROIDSDK = ${ANDROID_SDK_ROOT:-$ANDROID_HOME}
```

Derived binaries:

```text
sdkmanager = $ANDROIDSDK/cmdline-tools/latest/bin/sdkmanager
adb        = $ANDROIDSDK/platform-tools/adb
aapt       = $ANDROIDSDK/build-tools/36.0.0/aapt
NDK        = $ANDROIDSDK/ndk/28.2.13676358
```

Canonical compiler lane:

```text
Ubuntu       24.04
Python host  3.14
Java         17
Android API  36
Build tools  36.0.0
NDK          r28c / 28.2.13676358
NDK API      29
ABI          arm64-v8a
Bootstrap    webview
Package      art.eggiebagelface.samsungx400.python
```

## Build-candidate gates

The candidate remains RED until all of the following are proven by GitHub Actions:

1. APT dependency installation succeeds.
2. `requirements-build.txt` installs successfully.
3. `python -m pip check` is clean.
4. Cython/build/packaging/setuptools/wheel/virtualenv import sanity succeeds.
5. SDK manager, adb, aapt and NDK paths resolve.
6. Static Python and `.p4a` invariants pass.
7. p4a cross-compilation produces an APK.
8. `aapt` proves package id and `arm64-v8a` native payload.
9. `sanity.py` proves the APK contains Android manifest, dex, arm64 native payload and embedded Python without secret-like files.
10. SHA-256 and the complete build evidence bundle upload successfully.

## Copilot integration

Repository-wide instructions live in `.github/copilot-instructions.md`.

Android-specific instructions live in `.github/instructions/android-apk.instructions.md` and apply automatically when Copilot works on the APK template or its workflows.

`AGENTS.md` carries the equivalent standing contract for other AI agents.

Agents may propose or commit candidate fixes. They must not auto-merge PR #3, weaken the sanity gates, publish production releases, or bypass a package-specific PEP 517 failure by globally disabling build isolation.

## Nightly lane

Workflow: `.github/workflows/python3-apk-nightly.yml`

The nightly caller requests the reusable APK workflow with:

```text
checkout_ref = samsung-sm-x400-build-candidate
```

The cron is `17 8 * * *`, intentionally away from the top of the hour.

Important GitHub Actions rule: scheduled workflows run from the repository default branch. This repository's default branch is `main`. The nightly workflow is therefore staged on the candidate branch but does not become an autonomous schedule until the workflow definition is promoted to `main`. It can remain validation-only and must never auto-merge the candidate.

## Promotion path

```text
samsung-sm-x400-build-candidate
        |
        | CI green + human review
        v
samsung-sm-x400-backend
        |
        | PR #3 remains draft until its full checks are green
        v
samsung-sm-x400
```

No branch in this path is promoted solely because an AI agent reports confidence. CI artifact evidence is the gate.
