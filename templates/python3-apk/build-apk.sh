#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

: "${ANDROIDSDK:=${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}}"
: "${ANDROIDNDK:=${ANDROID_NDK_HOME:-}}"
: "${ANDROIDAPI:=36}"
: "${NDKAPI:=29}"

[[ -n "$ANDROIDSDK" && -d "$ANDROIDSDK" ]] || { echo "ANDROIDSDK/ANDROID_SDK_ROOT is required" >&2; exit 2; }
[[ -n "$ANDROIDNDK" && -d "$ANDROIDNDK" ]] || { echo "ANDROIDNDK/ANDROID_NDK_HOME is required" >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "python3 missing" >&2; exit 2; }
command -v java >/dev/null 2>&1 || { echo "java missing" >&2; exit 2; }
command -v p4a >/dev/null 2>&1 || { echo "p4a missing; install requirements-build.txt" >&2; exit 2; }

export ANDROIDSDK ANDROIDNDK ANDROIDAPI NDKAPI
export ANDROID_SDK_ROOT="$ANDROIDSDK"
export ANDROID_NDK_HOME="$ANDROIDNDK"

MODE="${BUILD_MODE:-debug}"
case "$MODE" in
  debug) P4A_MODE=(--debug) ;;
  release) P4A_MODE=(--release) ;;
  *) echo "BUILD_MODE must be debug or release" >&2; exit 64 ;;
esac

rm -rf dist
mkdir -p dist

p4a apk "${P4A_MODE[@]}"

mapfile -t apks < <(find . -type f -path '*/bin/*.apk' -print | sort)
(( ${#apks[@]} > 0 )) || { echo "p4a completed but no APK was found" >&2; exit 1; }

apk="${apks[-1]}"
cp "$apk" dist/samsung-sm-x400-python-${MODE}.apk
sha256sum dist/samsung-sm-x400-python-${MODE}.apk | tee dist/sha256.txt

python3 sanity.py dist/samsung-sm-x400-python-${MODE}.apk

echo "APK_GREEN $(cat dist/sha256.txt)"
