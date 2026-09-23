#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
COMPOSE="docker compose"

required_vars=(
  POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DATABASE_URL REDIS_URL
  DEFAULT_TENANT_ID
  TRENDYOL_SUPPLIER_ID TRENDYOL_API_KEY TRENDYOL_API_SECRET
  HEPSIBURADA_MERCHANT_ID HEPSIBURADA_USERNAME HEPSIBURADA_PASSWORD
)

fail() { echo "ERROR: $*" >&2; exit 1; }

[[ -f .env ]] || fail ".env bulunamadı. Önce: cp .env.example .env"
[[ "$(stat -c '%a' .env 2>/dev/null || stat -f '%Lp' .env)" == "600" ]] || fail ".env izinleri 600 olmalı"

for name in "${required_vars[@]}"; do
  value="$(grep -E "^${name}=" .env | tail -n 1 | cut -d= -f2- || true)"
  [[ -n "$value" && "$value" != *CHANGE_ME* ]] || fail "Eksik veya placeholder değer: ${name}"
done

command -v docker >/dev/null || fail "Docker kurulu değil"
$COMPOSE version >/dev/null || fail "Docker Compose kullanılamıyor"

echo "[1/5] Compose yapılandırması doğrulanıyor"
$COMPOSE config --quiet

echo "[2/5] Servisler build edilip başlatılıyor"
$COMPOSE up -d --build --remove-orphans

echo "[3/5] API health bekleniyor"
for attempt in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1/health >/dev/null; then
    break
  fi
  [[ "$attempt" -eq 30 ]] && fail "API health timeout"
  sleep 2
done

echo "[4/5] Database ve Redis sanity check"
"$ROOT_DIR/scripts/vps_sanity_check.sh"

echo "[5/5] Marketplace dry-run çalıştırılıyor (ürün gönderilmez)"
$COMPOSE exec -T api python scripts/dry_run_marketplace.py --marketplace all

echo "Deployment tamamlandı. Canlı marketplace çağrıları için MARKETPLACE_DRY_RUN=false ayarlayın."
