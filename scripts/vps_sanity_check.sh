#!/usr/bin/env bash
set -Eeuo pipefail

COMPOSE="docker compose"
FAILED=0

check() {
  local name="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    printf 'OK   %s\n' "$name"
  else
    printf 'FAIL %s\n' "$name"
    FAILED=1
  fi
}

$COMPOSE ps
check "PostgreSQL health" $COMPOSE exec -T postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
check "Redis health" $COMPOSE exec -T redis redis-cli ping
check "API health" curl --fail --silent --show-error http://127.0.0.1/health
check "Frontend HTTP" curl --fail --silent --show-error -I http://127.0.0.1/
check "Compose network" $COMPOSE exec -T api getent hosts postgres
check "Compose network Redis" $COMPOSE exec -T api getent hosts redis

if [[ "$FAILED" -ne 0 ]]; then
  echo "Sanity check failed. Inspect: docker compose logs --tail=200 api scheduler postgres redis"
  exit 1
fi

echo "Sanity check passed."
