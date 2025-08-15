#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Azure Ops Pack - Deploy Backend to Azure Container Apps (staging)

Creates a user-assigned managed identity, grants Key Vault secret get/list, and
deploys Container App 'forge1-backend' with external ingress on port 8000 using
image from ACR. Environment variables are injected via Key Vault secret references.

Usage:
  bash scripts/azure/40_deploy_backend_ca.sh
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

ACR_LOGIN=$(az acr show -n "$ACR" --query loginServer -o tsv)
ACR_ID=$(az acr show -n "$ACR" --query id -o tsv)
IMAGE="$ACR_LOGIN/forge1-backend:staging"

IDENTITY_NAME="id-forge1-${SUFFIX}"
CONTAINERAPP_NAME="forge1-backend"

info "Ensuring User-Assigned Managed Identity: $IDENTITY_NAME"
IDENTITY_ID=$(az identity show -g "$RG" -n "$IDENTITY_NAME" --query id -o tsv 2>/dev/null || true)
if [[ -z "$IDENTITY_ID" ]]; then
  IDENTITY_ID=$(az identity create -g "$RG" -n "$IDENTITY_NAME" -l "$LOC" --query id -o tsv)
fi
PRINCIPAL_ID=$(az identity show -g "$RG" -n "$IDENTITY_NAME" --query principalId -o tsv)

info "Granting Key Vault get,list to identity on $KV"
RBAC_ENABLED=$(az keyvault show -g "$RG" -n "$KV" --query properties.enableRbacAuthorization -o tsv 2>/dev/null || echo "false")
if [[ "$RBAC_ENABLED" == "true" ]]; then
  info "Vault $KV has RBAC enabled; skipping access policy and assigning RBAC role instead"
  VAULT_ID=$(az keyvault show -g "$RG" -n "$KV" --query id -o tsv)
  az role assignment create \
    --assignee-object-id "$PRINCIPAL_ID" \
    --assignee-principal-type ServicePrincipal \
    --role "Key Vault Secrets User" \
    --scope "$VAULT_ID" -o none || true
else
  az keyvault set-policy -n "$KV" --secret-permissions get list --object-id "$PRINCIPAL_ID" -o none
fi

info "Granting AcrPull on ACR to identity"
az role assignment create --assignee "$PRINCIPAL_ID" --role "AcrPull" --scope "$ACR_ID" -o none || true

info "Ensuring Container App Environment exists: $ACA_ENV"
az containerapp env show -g "$RG" -n "$ACA_ENV" -o none >/dev/null 2>&1 || die "Container Apps Environment $ACA_ENV not found. Run 10_bootstrap_core.sh first."

info "Deploying/Updating Container App: $CONTAINERAPP_NAME"
az containerapp up \
  --name "$CONTAINERAPP_NAME" \
  --resource-group "$RG" \
  --environment "$ACA_ENV" \
  --image "$IMAGE" \
  --ingress external \
  --target-port 8000 \
  --registry-server "$ACR_LOGIN" \
  --registry-identity "$IDENTITY_ID"

az containerapp identity assign -g "$RG" -n "$CONTAINERAPP_NAME" --user-assigned "$IDENTITY_ID" -o none || true

info "Configuring secrets from Key Vault..."
VAULT_URI=$(az keyvault show -g "$RG" -n "$KV" --query properties.vaultUri -o tsv)
VAULT_URI_NO_SLASH=${VAULT_URI%/}
az containerapp secret set -g "$RG" -n "$CONTAINERAPP_NAME" \
  --secrets \
    database-url=keyvaultref:$VAULT_URI_NO_SLASH/secrets/DATABASE-URL,identityref:$IDENTITY_ID \
    redis-url=keyvaultref:$VAULT_URI_NO_SLASH/secrets/REDIS-URL,identityref:$IDENTITY_ID \
  -o none

info "Setting environment variables to reference secrets..."
az containerapp update -g "$RG" -n "$CONTAINERAPP_NAME" \
  --set-env-vars \
    ENV=staging \
    DATABASE_URL=secretref:database-url \
    REDIS_URL=secretref:redis-url \
  -o none

FQDN=$(az containerapp show -g "$RG" -n "$CONTAINERAPP_NAME" --query properties.configuration.ingress.fqdn -o tsv)
echo "$FQDN"
echo "$FQDN" > .azure/backend.fqdn

exit 0

#!/usr/bin/env bash
set -euo pipefail

# Deploy backend to Azure Container Apps with Key Vault secret references
# Usage: bash scripts/azure/40_deploy_backend_ca.sh

if [[ ! -f .azure/env.staging ]]; then
  echo ".azure/env.staging not found. Run 10_bootstrap_core.sh first." >&2
  exit 1
fi
source .azure/env.staging

LOGIN_SERVER=$(az acr show -n "$ACR" --query loginServer -o tsv)
IMAGE="$LOGIN_SERVER/forge1-backend:staging"

echo "Ensuring managed identity for app"
MI_NAME="mi-forge1-${SUFFIX}"
az identity create -g "$RG" -n "$MI_NAME" -o none || true
MI_PRINCIPAL_ID=$(az identity show -g "$RG" -n "$MI_NAME" --query principalId -o tsv)
MI_ID=$(az identity show -g "$RG" -n "$MI_NAME" --query id -o tsv)

echo "Granting Key Vault access to managed identity"
az keyvault set-policy -n "$KV" --secret-permissions get list --object-id "$MI_PRINCIPAL_ID" -o none

echo "Deploying Container App forge1-backend"
APP_NAME="forge1-backend"
VAULT_URI=$(az keyvault show -n "$KV" --query properties.vaultUri -o tsv)

az containerapp create \
  -g "$RG" -n "$APP_NAME" \
  --image "$IMAGE" \
  --environment "$ACA_ENV" \
  --ingress external --target-port 8000 \
  --min-replicas 1 --max-replicas 3 \
  --registry-server "$LOGIN_SERVER" --registry-identity system \
  --user-assigned "${MI_ID}" \
  --env-vars \
    ENV=staging \
    JWT_SECRET=secretref:JWT-SECRET@$KV \
    OPENROUTER_API_KEY=secretref:OPENROUTER-API-KEY@$KV \
    DATABASE_URL=secretref:DATABASE-URL@$KV \
    REDIS_URL=secretref:REDIS-URL@$KV \
    BACKEND_CORS_ORIGINS=secretref:BACKEND-CORS-ORIGINS@$KV \
    AI_COMMS_DASHBOARD_ENABLED=true \
    INTERCONNECT_ENABLED=true \
  -o none || az containerapp update \
  -g "$RG" -n "$APP_NAME" \
  --image "$IMAGE" \
  --user-assigned "${MI_ID}" \
  --env-vars \
    ENV=staging \
    JWT_SECRET=secretref:JWT-SECRET@$KV \
    OPENROUTER_API_KEY=secretref:OPENROUTER-API-KEY@$KV \
    DATABASE_URL=secretref:DATABASE-URL@$KV \
    REDIS_URL=secretref:REDIS-URL@$KV \
    BACKEND_CORS_ORIGINS=secretref:BACKEND-CORS-ORIGINS@$KV \
    AI_COMMS_DASHBOARD_ENABLED=true \
    INTERCONNECT_ENABLED=true \
  -o none

FQDN=$(az containerapp show -g "$RG" -n "$APP_NAME" --query properties.configuration.ingress.fqdn -o tsv)
echo "Backend deployed. FQDN: https://$FQDN"


