---
applyTo: "templates/python3-apk/**,.github/workflows/python3-apk-*.yml"
---

# Samsung SM-X400 APK build instructions

Treat the Android APK lane as a reproducible cross-compile pipeline, not a normal desktop pip application.

- Preserve Android API 36, build-tools 36.0.0, NDK r28c (`28.2.13676358`), NDK API 29, Java 17, host Python 3.14, ABI `arm64-v8a`, WebView bootstrap, and package id `art.eggiebagelface.samsungx400.python` unless the task explicitly changes architecture.
- Keep host APT packages in `templates/python3-apk/apt-build-dependencies.txt`.
- Keep host Python build packages in `templates/python3-apk/requirements-build.txt`.
- Keep packaged app Python requirements in `templates/python3-apk/requirements-app.txt` and mirror them in `.p4a` after the p4a-provided `python3` requirement.
- Keep the host Python graph compatible with `python-for-android==2026.5.9`: use `Cython==0.29.36` and preserve p4a's `wheel~=0.43.0` constraint. Do not independently upgrade cross-compile tooling merely because a newer desktop package exists.
- The explicit host requirements mirror p4a's v2026.05.09 install graph so `pip check` can validate the complete candidate environment.
- Derive Android binaries from `${ANDROID_SDK_ROOT:-$ANDROID_HOME}`. Canonical binary paths are `cmdline-tools/latest/bin/sdkmanager`, `platform-tools/adb`, and `build-tools/36.0.0/aapt`.
- Never commit SDK absolute paths from a developer workstation.
- Do not globally disable PEP 517/build isolation as a first-line fix. Identify the failing package and use the appropriate p4a recipe or explicit host prerequisite.
- Keep services loopback-only by default and never place API keys, signing keys, credentials, `.env` files, model weights, or provider secrets in the APK template.
- Run or preserve CI checks for `pip check`, host build-module imports, Python compilation, `.p4a` invariants, SDK/NDK existence, p4a cross-compilation, APK package/ABI identity, APK sanity, SHA-256 creation and artifact upload.
- Candidate and nightly builds may produce evidence and artifacts. They must not automatically merge PRs or publish a production release.
