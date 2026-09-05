#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

echo '=== KAI9000 DEV / SM-X400 BOOTSTRAP ==='

if ! command -v pkg >/dev/null 2>&1; then
  echo 'ERROR: run this inside Termux on the SM-X400.' >&2
  exit 2
fi

# KAI Android vendor doctrine:
# - Termux package recipes are the approved Android downstream patch layer.
# - Python and Godot versions are reviewed in manifests/oss-vendors.lock.json.
# - Do not replace these with random GitHub fork install scripts.

pkg update -y
pkg install -y x11-repo
pkg update -y
pkg install -y \
  build-essential \
  clang \
  cmake \
  ninja \
  pkg-config \
  git \
  python \
  godot \
  openjdk-17 \
  curl \
  jq \
  unzip \
  zip

python -m ensurepip --upgrade >/dev/null 2>&1 || true
python -m pip install --upgrade pip setuptools wheel

EXPECTED_PYTHON='3.14.6'
EXPECTED_GODOT='4.7.2'
ACTUAL_PYTHON="$(python -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
ACTUAL_GODOT="$(godot --version 2>/dev/null || true)"

if [ "$ACTUAL_PYTHON" != "$EXPECTED_PYTHON" ]; then
  echo "ERROR: Python vendor drift: expected $EXPECTED_PYTHON, got $ACTUAL_PYTHON" >&2
  echo 'Review manifests/oss-vendors.lock.json before accepting a new runtime.' >&2
  exit 3
fi

case "$ACTUAL_GODOT" in
  "$EXPECTED_GODOT"*) ;;
  *)
    echo "ERROR: Godot vendor drift: expected $EXPECTED_GODOT.x, got ${ACTUAL_GODOT:-missing}" >&2
    echo 'Review manifests/oss-vendors.lock.json before accepting a new runtime.' >&2
    exit 4
    ;;
esac

python3 scripts/vendor_sanity.py

echo
echo "Python downstream: $ACTUAL_PYTHON"
echo "Godot downstream:  $ACTUAL_GODOT"
echo 'Bootstrap complete.'
echo 'Next: bash samsung-sm-x400/kai9000_dev/scripts/sanity.sh'
