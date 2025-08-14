#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Azure Ops Pack - Run Full Staging Deployment

Runs the end-to-end flow:
  1) 05_check_prereqs
  2) 00_register_providers
  3) 10_bootstrap_core
  4) Optional: 15_create_datastores (--create-pg/--create-redis)
  5) 20_seed_keyvault_staging (prompts for values if not set in env)
  6) 30_build_push_backend
  7) 40_deploy_backend_ca
  8) 50_smoke_backend

Usage:
  bash scripts/azure/run_staging.sh
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "$0")/../../" && pwd)"
SCRIPT_DIR="$ROOT_DIR/scripts/azure"

echo "[1/8] Checking prerequisites..."
bash "$SCRIPT_DIR/05_check_prereqs.sh"

echo "[2/8] Registering providers..."
bash "$SCRIPT_DIR/00_register_providers.sh"

echo "[3/8] Bootstrapping core Azure resources..."
bash "$SCRIPT_DIR/10_bootstrap_core.sh"

echo "Would you like to create managed datastores now (Azure Postgres & Redis)? [y/N]"
read -r CREATE_DS
if [[ "$CREATE_DS" =~ ^[Yy]$ ]]; then
  echo "[4/8] Creating datastores..."
  bash "$SCRIPT_DIR/15_create_datastores.sh" --create-pg --create-redis || true
else
  echo "Skipping datastore creation."
fi

echo "[5/8] Seeding Key Vault for staging..."
bash "$SCRIPT_DIR/20_seed_keyvault_staging.sh"

echo "[6/8] Building and pushing backend image..."
bash "$SCRIPT_DIR/30_build_push_backend.sh" --context "$ROOT_DIR" --tag staging

echo "[7/8] Deploying Container App..."
FQDN=$(bash "$SCRIPT_DIR/40_deploy_backend_ca.sh")
echo "$FQDN" > "$ROOT_DIR/.azure/backend.fqdn"

echo "[8/8] Smoke testing..."
bash "$SCRIPT_DIR/50_smoke_backend.sh" --url "https://$FQDN"

echo
echo "Deployment complete."
echo "Backend FQDN: https://$FQDN"
echo "Next steps:"
echo " - Set your frontend VITE_API_BASE_URL to https://$FQDN"
echo " - Add that origin to BACKEND_CORS_ORIGINS in Key Vault"
echo " - Run database migrations if needed"

exit 0


