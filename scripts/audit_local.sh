#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:5173}"
APP_DB_URL_DEFAULT="postgresql://forge:forge@127.0.0.1:5542/forge1_local"
ALEMBIC_DB_URL_DEFAULT="postgresql+psycopg://forge:forge@127.0.0.1:5542/forge1_local"

# Resolve repo root for path-stable operations regardless of current working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "[0/7] Ensuring local services (postgres, redis) are up..."
docker compose -f "${REPO_ROOT}/docker-compose.local.yml" up -d postgres redis >/dev/null 2>&1 || true

echo "[1/7] Waiting for postgres to be healthy..."
for i in {1..30}; do
  status=$(docker inspect -f '{{.State.Health.Status}}' forge1_local_postgres 2>/dev/null || echo "")
  if [[ "$status" == "healthy" ]]; then
    break
  fi
  sleep 1
done

echo "[2/7] Ensuring database 'forge1_local' and pgvector extension exist..."
PG_HOST=127.0.0.1 PG_PORT=5542 PGUSER=forge PGPASSWORD=forge \
psql -w -h 127.0.0.1 -p 5542 -U forge -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='forge1_local'" | grep -q 1 || \
  PGPASSWORD=forge psql -w -h 127.0.0.1 -p 5542 -U forge -d postgres -c "CREATE DATABASE forge1_local;"
PG_HOST=127.0.0.1 PG_PORT=5542 PGUSER=forge PGPASSWORD=forge \
psql -w -h 127.0.0.1 -p 5542 -U forge -d forge1_local -c "CREATE EXTENSION IF NOT EXISTS vector;" || true

echo "[3/7] Exporting DATABASE_URL for app runtime and preparing Alembic URL..."
export DATABASE_URL="${DATABASE_URL:-$APP_DB_URL_DEFAULT}"
export ALEMBIC_DATABASE_URL="${ALEMBIC_DATABASE_URL:-$ALEMBIC_DB_URL_DEFAULT}"
echo "DATABASE_URL=${DATABASE_URL}"
echo "ALEMBIC_DATABASE_URL=${ALEMBIC_DATABASE_URL}"

echo "[4/7] Running alembic migrations (idempotent)..."
pushd "${REPO_ROOT}/backend" >/dev/null
SQLALCHEMY_DATABASE_URL="${ALEMBIC_DATABASE_URL}" alembic upgrade head || {
  echo "Alembic failed"; exit 1;
}
popd >/dev/null

echo "[5/7] Checking backend /api/v1/health/live..."
curl -sS "${API_BASE_URL}/api/v1/health/live" | jq . || curl -sS "${API_BASE_URL}/api/v1/health/live" || true

echo "[6/7] Checking backend readiness..."
curl -sS "${API_BASE_URL}/api/v1/health/ready" | jq . || curl -sS "${API_BASE_URL}/api/v1/health/ready" || true

echo "[7/7] Authenticating (demo login)..."
TOKEN=$(curl -sS -X POST -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin" \
  "${API_BASE_URL}/api/v1/auth/login" | jq -r .access_token || true)
if [[ -z "${TOKEN}" || "${TOKEN}" == "null" ]]; then
  echo "WARN: Could not obtain token. Make sure ENV=dev or local and demo user exists. Continuing unauthenticated for public endpoints."
else
  echo "Obtained token"
fi

echo "[4/5] Checking metrics summary/trends/activity..."
if [[ -n "${TOKEN:-}" && "${TOKEN}" != "null" ]]; then
  curl -sS -H "Authorization: Bearer ${TOKEN}" "${API_BASE_URL}/api/v1/metrics/summary?hours=24" | jq . || true
  curl -sS -H "Authorization: Bearer ${TOKEN}" "${API_BASE_URL}/api/v1/metrics/trends?hours=6&bucket_minutes=30" | jq . || true
  curl -sS -H "Authorization: Bearer ${TOKEN}" "${API_BASE_URL}/api/v1/metrics/activity?limit=10" | jq . || true
else
  curl -sS "${API_BASE_URL}/api/v1/metrics/summary?hours=24" | jq . || true
  curl -sS "${API_BASE_URL}/api/v1/metrics/trends?hours=6&bucket_minutes=30" | jq . || true
  curl -sS "${API_BASE_URL}/api/v1/metrics/activity?limit=10" | jq . || true
fi

echo "[5/5] Checking frontend UI..."
code=$(
  curl -sS -o /dev/null -w "%{http_code}" "${FRONTEND_URL}"
)
echo "Frontend GET / => HTTP ${code}"
if [[ "${code}" != "200" && "${code}" != "304" ]]; then
  echo "WARN: Frontend may not be running at ${FRONTEND_URL}"
fi

echo "Done."


