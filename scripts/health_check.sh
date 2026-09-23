#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
COMPOSE="docker compose"

fail() { echo "ERROR: $*" >&2; exit 1; }
[[ -f .env ]] || fail ".env bulunamadı"

required_vars=(
  DATABASE_URL REDIS_URL
  TRENDYOL_SUPPLIER_ID TRENDYOL_API_KEY TRENDYOL_API_SECRET
  HEPSIBURADA_MERCHANT_ID HEPSIBURADA_USERNAME HEPSIBURADA_PASSWORD
)
for name in "${required_vars[@]}"; do
  value="$(grep -E "^${name}=" .env | tail -n 1 | cut -d= -f2- || true)"
  [[ -n "$value" && "$value" != *CHANGE_ME* ]] || fail "Eksik veya placeholder değer: ${name}"
done

echo "== Container health =="
$COMPOSE ps
curl --fail --silent --show-error http://127.0.0.1/health >/dev/null
echo "OK API /health"
$COMPOSE exec -T postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
echo "OK PostgreSQL"
[[ "$($COMPOSE exec -T redis redis-cli ping | tr -d '\r')" == "PONG" ]] || fail "Redis ping başarısız"
echo "OK Redis"

echo "== Read-only marketplace credential/connectivity check =="
$COMPOSE exec -T api python - <<'PY'
import asyncio
from app.config import get_settings
from app.integrations.hepsiburada import HepsiburadaClient
from app.integrations.trendyol import TrendyolClient

async def main():
    settings = get_settings()
    clients = [TrendyolClient(settings), HepsiburadaClient(settings)]
    try:
        for name, client in zip(("Trendyol", "Hepsiburada"), clients):
            await client.get_categories()
            print(f"OK {name} credentials and read-only categories request")
    finally:
        for client in clients:
            await client.close()

asyncio.run(main())
PY

echo "Health check passed. No product create or stock update request was sent."
