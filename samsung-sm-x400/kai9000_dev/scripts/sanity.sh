#!/data/data/com.termux/files/usr/bin/bash
set -u

PASS=0
WARN=0
FAIL=0

pass(){ printf '[GREEN] %s\n' "$*"; PASS=$((PASS+1)); }
warn(){ printf '[AMBER] %s\n' "$*"; WARN=$((WARN+1)); }
fail(){ printf '[RED] %s\n' "$*"; FAIL=$((FAIL+1)); }

check_cmd(){
  if command -v "$1" >/dev/null 2>&1; then
    pass "$1 present"
  else
    fail "$1 missing"
  fi
}

echo '=== KAI9000 DEV / SM-X400 SANITY ==='
printf 'uname: '; uname -a
printf 'arch:  '; uname -m

for c in git python clang cmake ninja pkg-config java curl jq; do
  check_cmd "$c"
done

case "$(uname -m)" in
  aarch64|arm64) pass 'arm64 host detected' ;;
  *) warn "expected arm64/aarch64 tablet host, got $(uname -m)" ;;
esac

if [ -n "${PREFIX:-}" ] && [[ "$PREFIX" == *com.termux* ]]; then
  pass 'Termux prefix detected'
else
  warn 'Termux prefix not detected'
fi

if command -v python >/dev/null 2>&1; then
  python - <<'PY'
import platform, sys
print('[INFO] python:', sys.version.split()[0])
print('[INFO] platform:', platform.platform())
PY
fi

if command -v ninja >/dev/null 2>&1; then
  printf '[INFO] ninja: '; ninja --version
fi
if command -v cmake >/dev/null 2>&1; then
  cmake --version | head -1 | sed 's/^/[INFO] /'
fi
if command -v clang >/dev/null 2>&1; then
  clang --version | head -1 | sed 's/^/[INFO] /'
fi

echo
echo "GREEN=$PASS AMBER=$WARN RED=$FAIL"
[ "$FAIL" -eq 0 ]
