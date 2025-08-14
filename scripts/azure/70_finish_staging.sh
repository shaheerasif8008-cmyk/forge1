#!/usr/bin/env bash
set -euo pipefail

# Load Azure env
if [[ ! -f .azure/env.staging ]]; then
  echo "ERROR: .azure/env.staging not found. Run 10_bootstrap_core.sh first."
  exit 1
fi
# shellcheck disable=SC1091
source .azure/env.staging

echo "[1/4] ACR health + auth"
ACR_LOGIN=$(az acr show -g "$RG" -n "$ACR" --query loginServer -o tsv)
az acr check-health -n "$ACR" --yes || true
az acr login -n "$ACR"

echo "[2/4] Buildx bootstrap + build/push (linux/amd64)"
docker buildx create --name forge1builder --use >/dev/null 2>&1 || true
docker buildx use forge1builder
docker buildx inspect --bootstrap >/dev/null

attempt_push () {
  bash scripts/azure/30_build_push_backend.sh --context . --tag staging
}
# retry up to 3 times for transient ACR TLS hiccups
n=0; until attempt_push; do n=$((n+1)); [[ $n -ge 3 ]] && { echo "Push failed after 3 attempts"; exit 1; }; echo "Retrying push ($n/3)..." && sleep 5; done

echo "[3/4] Deploy Container App"
bash scripts/azure/40_deploy_backend_ca.sh

FQDN=$(az containerapp show -g "$RG" -n forge1-backend --query properties.configuration.ingress.fqdn -o tsv)
API_URL="https://$FQDN"
echo "[4/4] Smoke test: $API_URL"
bash scripts/azure/50_smoke_backend.sh --url "$API_URL"

cat <<EOF

✅ Forge 1 staging is live.

Backend staging URL:
$API_URL

Next steps:
- If you haven't run DB migrations on Azure Postgres yet:
    export DATABASE_URL="<paste the exact DATABASE_URL you stored in Key Vault>"
    alembic upgrade head
- To wire the frontend, set VITE_API_BASE_URL=$API_URL and deploy your UI.
EOF

