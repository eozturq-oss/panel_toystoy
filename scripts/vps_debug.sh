#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE="${1:-api}"
LINES="${LINES:-200}"

echo "== Service status =="
docker compose ps

echo "== Recent logs: ${SERVICE} =="
docker compose logs --tail="$LINES" --timestamps "$SERVICE"

echo "== API/Scheduler error lines =="
docker compose logs --no-color --tail="$LINES" api scheduler 2>&1 | grep -Ei 'error|exception|timeout|429|401|403|5[0-9]{2}|connection refused|rate limit|failed' || true

echo "== Internal DNS =="
docker compose exec -T api getent hosts postgres redis || true

echo "== Database connectivity =="
docker compose exec -T postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' || true

echo "== Redis connectivity =="
docker compose exec -T redis redis-cli ping || true

echo "== Container network =="
docker network inspect "$(basename "$PWD")_app_net" --format '{{range .Containers}}{{.Name}} {{.IPv4Address}}{{"\n"}}{{end}}' 2>/dev/null || true

echo "== Recent API health =="
curl --fail --silent --show-error --max-time 5 http://127.0.0.1/health || true
echo
