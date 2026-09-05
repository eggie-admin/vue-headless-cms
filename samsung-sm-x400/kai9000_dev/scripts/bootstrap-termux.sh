#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

echo '=== KAI9000 DEV / SM-X400 BOOTSTRAP ==='

if ! command -v pkg >/dev/null 2>&1; then
  echo 'ERROR: run this inside Termux on the SM-X400.' >&2
  exit 2
fi

pkg update -y
pkg install -y \
  build-essential \
  clang \
  cmake \
  ninja \
  pkg-config \
  git \
  python \
  openjdk-17 \
  curl \
  jq \
  unzip \
  zip

python -m ensurepip --upgrade >/dev/null 2>&1 || true
python -m pip install --upgrade pip setuptools wheel

echo
echo 'Bootstrap complete.'
echo 'Next: bash samsung-sm-x400/kai9000_dev/scripts/sanity.sh'
