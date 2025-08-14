#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Azure Ops Pack - Seed Key Vault (staging)

Reads .azure/env.staging and seeds required Key Vault secrets for the backend.

Secrets set:
  OPENROUTER-API-KEY, DATABASE-URL, REDIS-URL, JWT-SECRET, BACKEND-CORS-ORIGINS

Environment overrides (non-interactive):
  OPENROUTER_API_KEY, DATABASE_URL, REDIS_URL, JWT_SECRET, BACKEND_CORS_ORIGINS

Usage:
  bash scripts/azure/20_seed_keyvault_staging.sh
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

prompt_secret OPENROUTER_API_KEY "Enter OPENROUTER_API_KEY"
prompt_secret DATABASE_URL "Enter DATABASE_URL (postgresql://...)"
prompt_secret REDIS_URL "Enter REDIS_URL (redis://...)"
prompt_secret JWT_SECRET "Enter JWT_SECRET (random, long)"
prompt_secret BACKEND_CORS_ORIGINS "Enter BACKEND_CORS_ORIGINS (comma-separated origins, no *)"

info "Seeding secrets into Key Vault: $KV"
kv_set_secret "$KV" OPENROUTER-API-KEY "$OPENROUTER_API_KEY"
kv_set_secret "$KV" DATABASE-URL "$DATABASE_URL"
kv_set_secret "$KV" REDIS-URL "$REDIS_URL"
kv_set_secret "$KV" JWT-SECRET "$JWT_SECRET"
kv_set_secret "$KV" BACKEND-CORS-ORIGINS "$BACKEND_CORS_ORIGINS"

info "Secret URIs:"
az keyvault secret list --vault-name "$KV" --query "[].{name:name,id:id}" -o table

exit 0

#!/usr/bin/env bash
set -euo pipefail

# Seed minimal secrets into Key Vault for staging
# Usage: bash scripts/azure/20_seed_keyvault_staging.sh

if [[ ! -f .azure/env.staging ]]; then
  echo ".azure/env.staging not found. Run 10_bootstrap_core.sh first." >&2
  exit 1
fi
source .azure/env.staging

require() {
  local name="$1"; shift
  local val
  val=${!name:-}
  if [[ -z "$val" ]]; then
    read -r -p "Enter value for $name: " val
  fi
  if [[ -z "$val" ]]; then
    echo "Missing value for $name" >&2
    exit 1
  fi
  echo "$val"
}

OPENROUTER_API_KEY=$(require OPENROUTER_API_KEY)
DATABASE_URL=$(require DATABASE_URL)
REDIS_URL=$(require REDIS_URL)
JWT_SECRET=$(require JWT_SECRET)
BACKEND_CORS_ORIGINS=$(require BACKEND_CORS_ORIGINS)

echo "Setting secrets in Key Vault $KV"
az keyvault secret set --vault-name "$KV" --name OPENROUTER-API-KEY --value "$OPENROUTER_API_KEY" -o none
az keyvault secret set --vault-name "$KV" --name DATABASE-URL --value "$DATABASE_URL" -o none
az keyvault secret set --vault-name "$KV" --name REDIS-URL --value "$REDIS_URL" -o none
az keyvault secret set --vault-name "$KV" --name JWT-SECRET --value "$JWT_SECRET" -o none
az keyvault secret set --vault-name "$KV" --name BACKEND-CORS-ORIGINS --value "$BACKEND_CORS_ORIGINS" -o none

echo "Secrets seeded. Vault URI: $(az keyvault show -n "$KV" --query properties.vaultUri -o tsv)"


