#!/usr/bin/env bash
set -euo pipefail

# Usage: ./foundry_deploy.sh <resource_group> <workspace> <endpoint_name> <acr_name> <keyvault_name> <tag>
# Example: ./foundry_deploy.sh rg-ai foundry-ws forge1-backend myacr my-kv v1

RG=${1:-}
WS=${2:-}
ENDPOINT=${3:-forge1-backend}
ACR=${4:-}
KV=${5:-}
TAG=${6:-latest}

if [[ -z "$RG" || -z "$WS" || -z "$ACR" || -z "$KV" ]]; then
  echo "Usage: $0 <resource_group> <workspace> <endpoint_name> <acr_name> <keyvault_name> <tag>" >&2
  exit 1
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
SPEC_TEMPLATE="${SCRIPT_DIR}/foundry_deploy.json"
ACR_REGISTRY="${ACR}.azurecr.io"
KEYVAULT_URI=$(az keyvault show -n "$KV" -g "$RG" --query properties.vaultUri -o tsv)

TMP_SPEC=$(mktemp)
sed \
  -e "s#\${ACR_REGISTRY}#${ACR_REGISTRY}#g" \
  -e "s#\${KEYVAULT_URI}#${KEYVAULT_URI}#g" \
  -e "s#\${TAG}#${TAG}#g" \
  "$SPEC_TEMPLATE" > "$TMP_SPEC"

echo "Deploying to Azure AI Foundry workspace ${WS} endpoint ${ENDPOINT}"
az extension add --name ml -y >/dev/null 2>&1 || true
az ml online-endpoint create -n "$ENDPOINT" -g "$RG" -w "$WS" --traffic-config "{\"${ENDPOINT}\":100}" || true
az ml online-deployment create -n "${ENDPOINT}" -e "$ENDPOINT" -g "$RG" -w "$WS" --file "$TMP_SPEC" --all-traffic

echo "Deployment complete"


