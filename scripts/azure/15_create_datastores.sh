#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Azure Ops Pack - Optional Datastores (Postgres & Redis)

Flags:
  --create-pg      Create Azure Database for PostgreSQL Flexible Server (GP D2s_v5)
  --create-redis   Create Azure Cache for Redis (Basic c0)

Uses .azure/env.staging for RG and LOC.

Usage:
  bash scripts/azure/15_create_datastores.sh [--create-pg] [--create-redis]

If no flags are provided, the script prints instructions and exits 0.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=./lib_common.sh
source "$SCRIPT_DIR/lib_common.sh"

read_env
ensure_logged_in

CREATE_PG=false
CREATE_REDIS=false

for arg in "$@"; do
  case "$arg" in
    --create-pg) CREATE_PG=true ;;
    --create-redis) CREATE_REDIS=true ;;
    *) die "Unknown flag: $arg" ;;
  esac
done

if [[ "$CREATE_PG" == false && "$CREATE_REDIS" == false ]]; then
  info "No flags provided. To create managed datastores, run with --create-pg and/or --create-redis."
  info "Alternatively, set DATABASE_URL and REDIS_URL to existing services."
  exit 0
fi

[[ -n "${RG:-}" && -n "${LOC:-}" && -n "${SUFFIX:-}" ]] || die ".azure/env.staging missing or incomplete. Run 10_bootstrap_core.sh first."

if [[ "$CREATE_PG" == true ]]; then
  PG_NAME="pg-forge1-${SUFFIX}"
  info "Ensuring Postgres Flexible Server: $PG_NAME in $RG ($LOC)"
  if ! az postgres flexible-server show -g "$RG" -n "$PG_NAME" >/dev/null 2>&1; then
    PG_PASS_GEN=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24)
    az postgres flexible-server create \
      --resource-group "$RG" \
      --name "$PG_NAME" \
      --location "$LOC" \
      --sku-name Standard_D2s_v5 \
      --tier GeneralPurpose \
      --storage-size 64 \
      --version 16 \
      --yes \
      --public-access 0.0.0.0-255.255.255.255 \
      --admin-user forge \
      --admin-password "$PG_PASS_GEN" \
      -o none
    az postgres flexible-server db create -g "$RG" -s "$PG_NAME" -d forge -o none || true
  fi
  PG_FQDN=$(az postgres flexible-server show -g "$RG" -n "$PG_NAME" --query fullyQualifiedDomainName -o tsv)
  if [[ -z "${PG_PASS_GEN:-}" ]]; then
    warn "Admin password was generated at creation time and not retrievable via CLI. If you created server earlier, use your stored password."
    info "Example DATABASE_URL: postgresql://forge:<PASSWORD>@${PG_FQDN}:5432/forge"
  else
    DATABASE_URL="postgresql://forge:${PG_PASS_GEN}@${PG_FQDN}:5432/forge"
    info "Postgres connection: $DATABASE_URL"
  fi
fi

if [[ "$CREATE_REDIS" == true ]]; then
  REDIS_NAME="redis-forge1-${SUFFIX}"
  info "Ensuring Azure Cache for Redis: $REDIS_NAME (Basic C0)"
  if ! az redis show -g "$RG" -n "$REDIS_NAME" >/dev/null 2>&1; then
    az redis create -g "$RG" -n "$REDIS_NAME" -l "$LOC" --sku Basic --vm-size c0 -o none
  fi
  REDIS_HOST=$(az redis show -g "$RG" -n "$REDIS_NAME" --query hostName -o tsv)
  REDIS_KEY=$(az redis list-keys -g "$RG" -n "$REDIS_NAME" --query primaryKey -o tsv)
  REDIS_URL="redis://:${REDIS_KEY}@${REDIS_HOST}:6379/1"
  info "Redis connection: $REDIS_URL"
fi

if command -v psql >/dev/null 2>&1 && [[ -n "${DATABASE_URL:-}" ]]; then
  info "Ensuring pgvector extension exists on database..."
  psql "$DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS vector;" || true
fi

info "Done. Remember to seed Key Vault with DATABASE-URL and REDIS-URL if using these services."

exit 0


