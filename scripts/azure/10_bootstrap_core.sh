#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Azure Ops Pack - Bootstrap Core Azure Resources (staging)

Creates Resource Group, ACR, Key Vault, Log Analytics Workspace, and Container Apps Environment.
Generates a short random suffix for unique names and writes .azure/env.staging.

Environment variables (optional overrides):
  RG        Resource group name (default: rg-forge1)
  LOC       Azure location (default: eastus)

Usage:
  bash scripts/azure/10_bootstrap_core.sh

Outputs:
  .azure/env.staging with variables: RG, LOC, SUFFIX, ACR, KV, LAW, ACA_ENV

USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=./lib_common.sh
source "$SCRIPT_DIR/lib_common.sh"

ensure_logged_in

mkdir -p .azure
read_env

RG=${RG:-rg-forge1}
LOC=${LOC:-eastus}

if [[ -f .azure/env.staging ]]; then
  info ".azure/env.staging found; reusing SUFFIX=${SUFFIX:-}"
fi

if [[ -z "${SUFFIX:-}" ]]; then
  SUFFIX=$(gen_suffix)
fi

ACR="${ACR:-acrforge1${SUFFIX}}"
KV="${KV:-kv-forge1-${SUFFIX}}"
LAW="${LAW:-log-forge1-${SUFFIX}}"
ACA_ENV="${ACA_ENV:-aca-env-forge1-${SUFFIX}}"

# Ensure required extension
az config set extension.use_dynamic_install=yes_without_prompt >/dev/null
az extension add -n containerapp -y >/dev/null 2>&1 || true
az extension update -n containerapp >/dev/null 2>&1 || true

info "Ensuring Resource Group: $RG ($LOC)"
az group create -n "$RG" -l "$LOC" -o none

info "Ensuring ACR: $ACR"
az acr show -g "$RG" -n "$ACR" >/dev/null 2>&1 || az acr create -g "$RG" -n "$ACR" --sku Basic -l "$LOC" -o none

info "Ensuring Key Vault: $KV"
az keyvault show -g "$RG" -n "$KV" >/dev/null 2>&1 || az keyvault create -g "$RG" -n "$KV" -l "$LOC" -o none

info "Ensuring Log Analytics Workspace: $LAW"
az monitor log-analytics workspace show -g "$RG" -n "$LAW" >/dev/null 2>&1 || az monitor log-analytics workspace create -g "$RG" -n "$LAW" -l "$LOC" -o none
LAW_ID=$(az monitor log-analytics workspace show -g "$RG" -n "$LAW" --query id -o tsv)
LAW_KEY=$(az monitor log-analytics workspace get-shared-keys -g "$RG" -n "$LAW" --query primarySharedKey -o tsv)

info "Ensuring Container Apps Environment: $ACA_ENV"
az containerapp env show -g "$RG" -n "$ACA_ENV" >/dev/null 2>&1 || az containerapp env create -g "$RG" -n "$ACA_ENV" -l "$LOC" \
  --logs-workspace-id "$LAW_ID" --logs-workspace-key "$LAW_KEY" -o none

ACR_LOGIN=$(az acr show -n "$ACR" --query loginServer -o tsv)

cat > .azure/env.staging <<EOF
RG=${RG}
LOC=${LOC}
SUFFIX=${SUFFIX}
ACR=${ACR}
KV=${KV}
LAW=${LAW}
ACA_ENV=${ACA_ENV}
ACR_LOGIN=${ACR_LOGIN}
EOF

info "ACR loginServer: $ACR_LOGIN"
info "ACA environment: $ACA_ENV"

exit 0

#!/usr/bin/env bash
set -euo pipefail

# Bootstrap core Azure resources for Forge 1 staging
# Usage: bash scripts/azure/10_bootstrap_core.sh

RG=${RG:-rg-forge1}
LOC=${LOC:-eastus}

# Generate 5-char random suffix (lowercase + digits)
SUFFIX=$(LC_ALL=C tr -dc 'a-z0-9' </dev/urandom | head -c 5)
ACR=acrforge1${SUFFIX}
KV=kv-forge1-${SUFFIX}
LAW=log-forge1-${SUFFIX}
ACA_ENV=aca-env-forge1-${SUFFIX}

echo "Creating resource group $RG in $LOC"
az group create -n "$RG" -l "$LOC" -o none

echo "Creating ACR $ACR"
az acr create -n "$ACR" -g "$RG" --sku Basic -l "$LOC" -o none

echo "Creating Key Vault $KV"
az keyvault create -n "$KV" -g "$RG" -l "$LOC" -o none

echo "Creating Log Analytics workspace $LAW"
az monitor log-analytics workspace create -g "$RG" -n "$LAW" -l "$LOC" -o none
LAW_ID=$(az monitor log-analytics workspace show -g "$RG" -n "$LAW" --query id -o tsv)

echo "Creating Container Apps environment $ACA_ENV"
az containerapp env create -n "$ACA_ENV" -g "$RG" -l "$LOC" --logs-destination log-analytics --logs-workspace-id "$LAW_ID" -o none

mkdir -p .azure
cat > .azure/env.staging <<EOF
RG=$RG
LOC=$LOC
SUFFIX=$SUFFIX
ACR=$ACR
KV=$KV
LAW=$LAW
ACA_ENV=$ACA_ENV
EOF

LOGIN_SERVER=$(az acr show -n "$ACR" --query loginServer -o tsv)
echo "ACR login server: $LOGIN_SERVER"
echo "ACA env name: $ACA_ENV"


