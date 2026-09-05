#!/usr/bin/env bash
set -euo pipefail

fail=0
check() {
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then
    printf '[GREEN] %s\n' "$label"
  else
    printf '[RED]   %s\n' "$label"
    fail=1
  fi
}

check 'nginx config' sudo nginx -t
check 'nginx active' systemctl is-active --quiet nginx
check 'mariadb active' systemctl is-active --quiet mariadb
check 'fastapi loopback health' curl -fsS --max-time 3 http://127.0.0.1:8000/health
check 'nginx loopback health' curl -fsS --max-time 3 http://127.0.0.1:8080/healthz

printf '\n--- LISTENERS ---\n'
ss -lntp || true

printf '\n--- FORBIDDEN WILDCARD PORTS ---\n'
if ss -lnt | grep -Eq '(^|[[:space:]])(0\.0\.0\.0|\[::\]):(3306|8000|11434)([[:space:]]|$)'; then
  echo '[RED] private KAI service exposed on wildcard address'
  fail=1
else
  echo '[GREEN] MariaDB/FastAPI/Ollama not exposed on wildcard TCP listeners'
fi

exit "$fail"
