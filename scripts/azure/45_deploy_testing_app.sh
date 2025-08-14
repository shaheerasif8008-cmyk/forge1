#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Azure Ops Pack - Deploy Testing App (optional)

Builds and deploys the testing-app as an Azure Container App using Key Vault secret references.

Flags:
  --internal   Use internal ingress (no public endpoint). Default: external ingress

Usage:
  bash scripts/azure/45_deploy_testing_app.sh [--internal]
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

INTERNAL=false
for arg in "$@"; do
  case "$arg" in
    --internal) INTERNAL=true ;;
    *) echo "Unknown flag: $arg" >&2; usage; exit 1 ;;
  esac
done

[[ -f .azure/env.staging ]] || { echo "ERROR: .azure/env.staging not found. Run 10_bootstrap_core.sh first." >&2; exit 2; }
source .azure/env.staging

az account show >/dev/null 2>&1 || { echo "ERROR: Not logged in. Run 'az login'" >&2; exit 2; }

ACR_LOGIN=$(az acr show -n "$ACR" --query loginServer -o tsv)
ACR_ID=$(az acr show -n "$ACR" --query id -o tsv)

echo "Logging in to ACR: $ACR"
az acr login -n "$ACR" >/dev/null

IMAGE_NAME="$ACR_LOGIN/testing-app:staging"

echo "Building testing-app image..."
docker build -f testing-app/Dockerfile -t "$IMAGE_NAME" testing-app
echo "Pushing testing-app image..."
docker push "$IMAGE_NAME"

IDENTITY_NAME="id-forge1-${SUFFIX}"
echo "Ensuring managed identity exists: $IDENTITY_NAME"
IDENTITY_ID=$(az identity show -g "$RG" -n "$IDENTITY_NAME" --query id -o tsv 2>/dev/null || true)
if [[ -z "$IDENTITY_ID" ]]; then
  IDENTITY_ID=$(az identity create -g "$RG" -n "$IDENTITY_NAME" -l "$LOC" --query id -o tsv)
fi
PRINCIPAL_ID=$(az identity show -g "$RG" -n "$IDENTITY_NAME" --query principalId -o tsv)

echo "Granting AcrPull on ACR to identity"
az role assignment create --assignee "$PRINCIPAL_ID" --role "AcrPull" --scope "$ACR_ID" -o none || true

echo "Granting Key Vault get,list to identity on $KV"
az keyvault set-policy -n "$KV" --secret-permissions get list --object-id "$PRINCIPAL_ID" -o none

APP_NAME="testing-app"
INGRESS_MODE="external"
[[ "$INTERNAL" == true ]] && INGRESS_MODE="internal"

echo "Deploying/Updating Container App: $APP_NAME ($INGRESS_MODE)"
az containerapp up \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --environment "$ACA_ENV" \
  --image "$IMAGE_NAME" \
  --ingress "$INGRESS_MODE" \
  --target-port 8002 \
  --registry-server "$ACR_LOGIN" \
  --registry-identity "$IDENTITY_ID" \
  -o none

az containerapp identity assign -g "$RG" -n "$APP_NAME" --identities "$IDENTITY_ID" -o none || true

echo "Configuring testing-app secrets from Key Vault..."
az containerapp secret set -g "$RG" -n "$APP_NAME" \
  --secrets \
    TESTING-OPENROUTER-API-KEY=keyvaultref://$KV/TESTING-OPENROUTER-API-KEY \
    TESTING-DATABASE-URL=keyvaultref://$KV/TESTING-DATABASE-URL \
    TESTING-REDIS-URL=keyvaultref://$KV/TESTING-REDIS-URL \
  -o none

echo "Setting environment variables to reference secrets..."
az containerapp update -g "$RG" -n "$APP_NAME" \
  --set-env-vars \
    ENV=testing \
    OPENROUTER_API_KEY=secretref:TESTING-OPENROUTER-API-KEY \
    DATABASE_URL=secretref:TESTING-DATABASE-URL \
    REDIS_URL=secretref:TESTING-REDIS-URL \
  -o none

FQDN=$(az containerapp show -g "$RG" -n "$APP_NAME" --query properties.configuration.ingress.fqdn -o tsv || true)
if [[ -n "$FQDN" ]]; then
  echo "Testing app FQDN: https://${FQDN}"
  echo "$FQDN" > .azure/testing_app.fqdn
else
  echo "Testing app deployed with internal ingress. No public FQDN."
fi

exit 0


