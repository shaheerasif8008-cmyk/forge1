#!/usr/bin/env bash
set -euo pipefail

# Disaster Recovery Failover Script (Azure)
# - Reads resources in primary RG
# - Spins up standby in secondary region
# - Syncs secrets from Key Vault
# - Points Traffic Manager (or Front Door) to secondary

usage() {
  cat <<EOF
Usage: $0 -g <resourceGroup> -p <primaryRegion> -s <secondaryRegion> [--dry-run]

Env:
  SUBSCRIPTION_ID           Azure subscription ID
  TRAFFIC_MANAGER_PROFILE   Name of Traffic Manager/Front Door profile
  KV_NAME                   Key Vault name in primary
  ACR_NAME                  ACR name
  ACA_ENV                   Container Apps Environment name
  ACA_BACKEND_APP           Container App name for backend
  ACA_FRONTEND_APP          Container App name for frontend (optional)

Example:
  $0 -g forge1-rg -p eastus -s westus2 --dry-run
EOF
}

DRY_RUN=0
RG=""
PRIMARY=""
SECONDARY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -g|--group) RG="$2"; shift 2;;
    -p|--primary) PRIMARY="$2"; shift 2;;
    -s|--secondary) SECONDARY="$2"; shift 2;;
    --dry-run) DRY_RUN=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1;;
  esac
done

if [[ -z "$RG" || -z "$PRIMARY" || -z "$SECONDARY" ]]; then
  echo "Missing required args" >&2
  usage
  exit 1
fi

az account show >/dev/null 2>&1 || { echo "Azure CLI not logged in" >&2; exit 1; }

say() { echo "[dr] $*"; }
doit() { if [[ "$DRY_RUN" -eq 1 ]]; then echo "+ $*"; else eval "$*"; fi }

say "Reading resources in primary RG=$RG region=$PRIMARY"
KV_NAME=${KV_NAME:-$(az keyvault list -g "$RG" --query "[0].name" -o tsv)}
ACR_NAME=${ACR_NAME:-$(az acr list -g "$RG" --query "[0].name" -o tsv)}
ACA_ENV=${ACA_ENV:-$(az containerapp env list -g "$RG" --query "[0].name" -o tsv)}
ACA_BACKEND_APP=${ACA_BACKEND_APP:-$(az containerapp list -g "$RG" --query "[?contains(name,'backend')].name | [0]" -o tsv)}

say "Primary: KV=$KV_NAME ACR=$ACR_NAME ACA_ENV=$ACA_ENV BACKEND=$ACA_BACKEND_APP"

say "Ensuring standby env in $SECONDARY"
STANDBY_ENV="${ACA_ENV}-dr"
doit az containerapp env create -g "$RG" -n "$STANDBY_ENV" -l "$SECONDARY" --logs-workspace-id "$(az monitor log-analytics workspace list -g "$RG" --query "[0].customerId" -o tsv)" --logs-workspace-key "$(az monitor log-analytics workspace list -g "$RG" --query "[0].listKeys().primarySharedKey" -o tsv)"

say "Syncing secrets from KV=$KV_NAME into ACI/ACA"
SECRETS_JSON=$(az keyvault secret list --vault-name "$KV_NAME" -o json)
# Example create app with env vars from KV
say "Deploying backend container app in secondary"
IMG="$(az acr show -n "$ACR_NAME" --query loginServer -o tsv)/backend:latest"
doit az containerapp create -g "$RG" -n "${ACA_BACKEND_APP}-dr" -e "$STANDBY_ENV" --image "$IMG" --env-vars "KV_SECRETS=$SECRETS_JSON" --ingress external --target-port 8000 || doit az containerapp update -g "$RG" -n "${ACA_BACKEND_APP}-dr" --image "$IMG"

say "Updating Traffic Manager/Front Door to point to secondary"
if [[ -n "${TRAFFIC_MANAGER_PROFILE:-}" ]]; then
  doit az network traffic-manager endpoint update -g "$RG" --profile-name "$TRAFFIC_MANAGER_PROFILE" -n secondary --type externalEndpoints --endpoint-status Enabled
  doit az network traffic-manager endpoint update -g "$RG" --profile-name "$TRAFFIC_MANAGER_PROFILE" -n primary --type externalEndpoints --endpoint-status Disabled
else
  say "TRAFFIC_MANAGER_PROFILE not set; skipping traffic update"
fi

say "Failover completed (dry-run=$DRY_RUN)"


