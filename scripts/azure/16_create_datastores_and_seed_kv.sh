#!/usr/bin/env bash
set -euo pipefail

here() { cd "$(dirname "$0")" >/dev/null 2>&1 && pwd; }
ROOT="$(here)/../.."
cd "$ROOT"

if [[ ! -f .azure/env.staging ]]; then
  echo "ERROR: .azure/env.staging not found. Run scripts/azure/10_bootstrap_core.sh first."
  exit 1
fi
# shellcheck disable=SC1091
source .azure/env.staging

# Defaults (overridable with flags)
DB_NAME="forge1"
PG_ADMIN="forgeadmin"
PG_PASSWORD=""
PG_SKU="Standard_B1ms"
PG_STORAGE_GB=32
PG_VERSION=14
REDIS_SKU="Basic"
REDIS_SIZE="c0"

# Parse flags
for arg in "$@"; do
  case $arg in
    --db-name=*)        DB_NAME="${arg#*=}";;
    --pg-admin=*)       PG_ADMIN="${arg#*=}";;
    --pg-password=*)    PG_PASSWORD="${arg#*=}";;
    --pg-sku=*)         PG_SKU="${arg#*=}";;
    --pg-storage-gb=*)  PG_STORAGE_GB="${arg#*=}";;
    --pg-version=*)     PG_VERSION="${arg#*=}";;
    --redis-sku=*)      REDIS_SKU="${arg#*=}";;
    --redis-size=*)     REDIS_SIZE="${arg#*=}";;
    *) echo "WARN: Unknown flag $arg";;
  esac
done

req() { command -v "$1" >/dev/null || { echo "ERROR: $1 not found"; exit 1; }; }
req az

PG="pg-forge1-$SUFFIX"
REDIS="redis-forge1-$SUFFIX"

echo "[1/6] Ensure PostgreSQL server: $PG"
set +e
az postgres flexible-server show -g "$RG" -n "$PG" >/dev/null 2>&1
EXISTS_PG=$?
set -e

if [[ $EXISTS_PG -ne 0 ]]; then
  if [[ -z "$PG_PASSWORD" ]]; then
    read -r -s -p "Enter Postgres admin password for $PG (will not echo): " PG_PASSWORD; echo ""
  fi
  az postgres flexible-server create \
    --resource-group "$RG" \
    --name "$PG" \
    --location "$LOC" \
    --admin-user "$PG_ADMIN" \
    --admin-password "$PG_PASSWORD" \
    --sku-name "$PG_SKU" \
    --storage-size "$PG_STORAGE_GB" \
    --tier "${PG_SKU%%_*}" \
    --version "$PG_VERSION" \
    --public-access 0.0.0.0-255.255.255.255 >/dev/null
else
  echo "Postgres exists. Skipping create."
  if [[ -z "$PG_PASSWORD" ]]; then
    read -r -s -p "Enter current Postgres admin password for $PG: " PG_PASSWORD; echo ""
  fi
fi

echo "[2/6] Ensure database: $DB_NAME (and pgvector)"
if command -v psql >/dev/null; then
  PGPASSWORD="$PG_PASSWORD" psql "host=${PG}.postgres.database.azure.com port=5432 dbname=postgres user=${PG_ADMIN} sslmode=require" \
    -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}';" | grep -q 1 || \
  PGPASSWORD="$PG_PASSWORD" psql "host=${PG}.postgres.database.azure.com port=5432 dbname=postgres user=${PG_ADMIN} sslmode=require" \
    -c "CREATE DATABASE ${DB_NAME};"
  PGPASSWORD="$PG_PASSWORD" psql "host=${PG}.postgres.database.azure.com port=5432 dbname=${DB_NAME} user=${PG_ADMIN} sslmode=require" \
    -c "CREATE EXTENSION IF NOT EXISTS vector;"
else
  echo "psql not found; skipping db create/pgvector. Do later with psql."
fi

echo "[3/6] Save DATABASE-URL to Key Vault: $KV"
ENC_PW="${PG_PASSWORD//@/%40}"; ENC_PW="${ENC_PW//:/%3A}"
DATABASE_URL="postgresql+psycopg://${PG_ADMIN}:${ENC_PW}@${PG}.postgres.database.azure.com:5432/${DB_NAME}?sslmode=require"
az keyvault secret set --vault-name "$KV" --name DATABASE-URL --value "$DATABASE_URL" >/dev/null

echo "[4/6] Ensure Redis: $REDIS"
set +e
az redis show -g "$RG" -n "$REDIS" >/dev/null 2>&1
EXISTS_REDIS=$?
set -e
if [[ $EXISTS_REDIS -ne 0 ]]; then
  az redis create -g "$RG" -n "$REDIS" --location "$LOC" --sku "$REDIS_SKU" --vm-size "$REDIS_SIZE" >/dev/null
else
  echo "Redis exists. Skipping create."
fi

echo "[5/6] Save REDIS-URL to Key Vault"
REDIS_KEY=$(az redis list-keys -g "$RG" -n "$REDIS" --query primaryKey -o tsv)
REDIS_URL="rediss://:${REDIS_KEY}@${REDIS}.redis.cache.windows.net:6380/0"
az keyvault secret set --vault-name "$KV" --name REDIS-URL --value "$REDIS_URL" >/dev/null

echo "[6/6] Done."

cat <<EOF

✅ Datastores ready.

DATABASE_URL (KV: DATABASE-URL):
$DATABASE_URL

REDIS_URL (KV: REDIS-URL):
$REDIS_URL

Next:
  bash scripts/azure/30_build_push_backend.sh
  bash scripts/azure/40_deploy_backend_ca.sh
  bash scripts/azure/50_smoke_backend.sh --url "https://\$(az containerapp show -g $RG -n forge1-backend --query properties.configuration.ingress.fqdn -o tsv)"
EOF

