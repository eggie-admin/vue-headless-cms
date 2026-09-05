# KAI 9000 DEV · Samsung SM-X400

Lean on-device developer forge for the Samsung SM-X400.

## Split of responsibility

**SM-X400 / Termux**
- Git checkout and edits
- Python 3 sanity tooling
- Clang/C/C++ compile probes
- CMake + Ninja fast local builds
- Godot project editing/runtime experiments
- ADB/device inspection when available

**GitHub Actions**
- canonical Android SDK/API 36 build
- Java 17
- Android build-tools / NDK provisioning
- Godot Android export
- APK signing checks, 16 KiB alignment checks and artifact upload

Do not turn the tablet into a fake Ubuntu x86_64 Android SDK host. Keep the Android packaging foundry in CI and use the tablet as the fast arm64 forge.

## Bootstrap on SM-X400

```bash
cd ~/storage/shared
# clone the repo if it is not already present
# git clone https://github.com/eggie-admin/vue-headless-cms.git
cd vue-headless-cms
git fetch origin
git switch samsung-sm-x400-kai9000-dev

bash samsung-sm-x400/kai9000_dev/scripts/bootstrap-termux.sh
bash samsung-sm-x400/kai9000_dev/scripts/sanity.sh
bash samsung-sm-x400/kai9000_dev/scripts/build-native.sh
```

## Canonical Android lane

- target/API: 36
- ABI: `arm64-v8a`
- Java: 17
- NDK: r28c (`28.2.13676358`)
- NDK API: 29
- build generator for native probes: Ninja
- APK production: repository GitHub Actions workflow `.github/workflows/android-apk.yml`

## Why Ninja

Ninja is the thin build executor. CMake generates the graph; Ninja executes only what changed. This is ideal on the tablet because incremental native checks stay quick and the CI runner remains the authority for the actual Android package.

## Commands

```bash
# doctor
bash samsung-sm-x400/kai9000_dev/scripts/sanity.sh

# clean native rebuild
rm -rf samsung-sm-x400/kai9000_dev/build/native
bash samsung-sm-x400/kai9000_dev/scripts/build-native.sh

# inspect tool versions
clang --version
cmake --version
ninja --version
python --version
git --version
java -version
```

## Guardrails

- no secrets in this folder
- no model-authored shell execution
- no Ollama public bind
- no `0.0.0.0` control plane
- local native success is **not** APK success
- GitHub artifact evidence is required before calling the Android build green
