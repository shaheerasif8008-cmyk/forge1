#!/usr/bin/env bash
set -euo pipefail

# ===== Helpers =====
here() { cd "$(dirname "$0")" >/dev/null 2>&1 && pwd; }
ROOT="$(here)/../.."
cd "$ROOT"

say() { printf "\033[1;34m[INFO]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[ERR ]\033[0m %s\n" "$*"; }
die() { err "$*"; exit 1; }

need() { command -v "$1" >/dev/null || die "Missing dependency: $1"; }

# ===== Preconditions =====
need az
test -f .azure/env.staging || die ".azure/env.staging not found. Run 10_bootstrap_core.sh first."
# shellcheck disable=SC1091
source .azure/env.staging

say "Ensuring Azure CLI login"
az account show >/dev/null 2>&1 || az login >/dev/null

: "${RG:?missing RG}"; : "${LOC:?missing LOC}"; : "${KV:?missing KV}"; : "${ACR:?missing ACR}"; : "${SUFFIX:?missing SUFFIX}"

# Determine backend URL
CA_NAME=${CA_NAME:-forge1-backend}
API_FQDN=$(az containerapp show -g "$RG" -n "$CA_NAME" --query properties.configuration.ingress.fqdn -o tsv)
API_URL="https://$API_FQDN"

# ===== 1) Read DATABASE_URL from Key Vault =====
say "Reading DATABASE-URL from Key Vault: $KV"
DATABASE_URL=$(az keyvault secret show --vault-name "$KV" --name DATABASE-URL --query value -o tsv)
if [[ -z "${DATABASE_URL:-}" ]]; then
  die "DATABASE-URL secret is empty or missing in Key Vault $KV"
fi
export DATABASE_URL

# ===== 2) Migrations (3 strategies) =====
MIGRATION_STATUS="not-run"
MIGRATION_STRATEGY=""

run_migrations_local() {
  if command -v alembic >/dev/null; then
    say "Running Alembic locally (backend/alembic.ini)"
    set +e
    (
      cd backend && alembic -c alembic.ini upgrade head
    )
    rc=$?
    set -e
    return $rc
  fi
  return 127
}

run_migrations_docker_offline() {
  # Generate SQL offline using python container, then apply via psql in postgres container
  if ! command -v docker >/dev/null; then
    return 127
  fi
  say "Running Alembic offline (docker) and applying via psql"
  TMP_SQL=$(mktemp)
  set +e
  docker run --rm -v "$PWD/backend":/app -w /app python:3.12-slim sh -lc '
    pip install -q --no-cache-dir -r requirements.txt && \
    alembic -c alembic.ini upgrade head --sql'
  gen_rc=$?
  set -e
  if [[ $gen_rc -ne 0 ]]; then
    warn "Failed to generate offline SQL"
    return 1
  fi | tee "$TMP_SQL" >/dev/null

  # Convert DB URL for psql (strip +driver)
  DB_URL_PSQL=$(python3 - <<'PY'
import os, re
u=os.environ.get('DATABASE_URL','')
u=re.sub(r"\+[^:]+", "", u, count=1)
print(u)
PY
)
  # Apply SQL via psql
  set +e
  docker run --rm -i -e PSQL_URL="$DB_URL_PSQL" postgres:16 sh -lc '
    cat > /tmp/m.sql; \
    psql "$PSQL_URL" -v ON_ERROR_STOP=1 -f /tmp/m.sql'
  apply_rc=$?
  set -e
  rm -f "$TMP_SQL"
  return $apply_rc
}

run_migrations_aca_job() {
  say "Running Alembic as Azure Container Apps Job"
  ACR_LOGIN=$(az acr show -n "$ACR" --query loginServer -o tsv)
  IMAGE="$ACR_LOGIN/forge1-backend:staging"
  JOB_NAME="forge1-migrate-$SUFFIX"

  # Registry credentials
  ACR_USER=$(az acr credential show -n "$ACR" --query username -o tsv)
  ACR_PASS=$(az acr credential show -n "$ACR" --query passwords[0].value -o tsv)

  set +e
  az containerapp job show -g "$RG" -n "$JOB_NAME" >/dev/null 2>&1
  exists=$?
  set -e

  CMD="/bin/sh"
  ARGS=("-lc" "python -m pip install --user -q 'psycopg[binary]==3.2.9' || true; alembic upgrade head")

  if [[ $exists -ne 0 ]]; then
    az containerapp job create \
      -g "$RG" -n "$JOB_NAME" \
      --environment "$ACA_ENV" \
      --trigger-type Manual \
      --replica-timeout 900 \
      --image "$IMAGE" \
      --registry-server "$ACR_LOGIN" \
      --registry-username "$ACR_USER" \
      --registry-password "$ACR_PASS" \
      --cpu 0.25 --memory 0.5Gi \
      --env-vars DATABASE_URL="$DATABASE_URL" \
      --command "$CMD" --args "${ARGS[@]}" >/dev/null
  else
    az containerapp job update \
      -g "$RG" -n "$JOB_NAME" \
      --image "$IMAGE" \
      --registry-server "$ACR_LOGIN" \
      --registry-username "$ACR_USER" \
      --registry-password "$ACR_PASS" \
      --env-vars DATABASE_URL="$DATABASE_URL" \
      --command "$CMD" --args "${ARGS[@]}" >/dev/null
  fi

  # Start execution
  az containerapp job start -g "$RG" -n "$JOB_NAME" >/dev/null
  # Poll latest execution status
  exec_name=""
  for i in {1..60}; do
    exec_name=$(az containerapp job execution list -g "$RG" -n "$JOB_NAME" --query "[-1].name" -o tsv 2>/dev/null || true)
    if [[ -n "$exec_name" ]]; then
      status=$(az containerapp job execution show -g "$RG" -n "$JOB_NAME" --name "$exec_name" --query properties.status -o tsv 2>/dev/null || echo "")
      if [[ "$status" == "Succeeded" || "$status" == "Failed" || "$status" == "Completed" ]]; then
        break
      fi
    fi
    sleep 5
  done

  if [[ -n "$exec_name" ]]; then
    say "Job execution: $exec_name"
    az containerapp job execution logs show -g "$RG" -n "$JOB_NAME" --name "$exec_name" --tail 100 || true
    status=$(az containerapp job execution show -g "$RG" -n "$JOB_NAME" --name "$exec_name" --query properties.status -o tsv 2>/dev/null || echo "")
  else
    warn "Could not determine job execution name"
    status="Unknown"
  fi

  # Cleanup job (idempotent)
  az containerapp job delete -g "$RG" -n "$JOB_NAME" -y >/dev/null 2>&1 || true

  [[ "$status" == "Succeeded" || "$status" == "Completed" ]] && return 0 || return 1
}

# Try strategies in order A, B, C
if run_migrations_local; then
  MIGRATION_STATUS="succeeded"
  MIGRATION_STRATEGY="local"
else
  if run_migrations_docker_offline; then
    MIGRATION_STATUS="succeeded"
    MIGRATION_STRATEGY="docker-offline"
  else
    if run_migrations_aca_job; then
      MIGRATION_STATUS="succeeded"
      MIGRATION_STRATEGY="aca-job"
    else
      MIGRATION_STATUS="failed"
      MIGRATION_STRATEGY="none"
    fi
  fi
fi

if [[ "$MIGRATION_STATUS" != "succeeded" ]]; then
  err "All migration strategies failed. Investigate local driver mismatch or network access."
  exit 1
fi

# ===== 3) Frontend publish (Azure Storage static website) =====
FRONTEND_URL=""
if [[ -d frontend && -f frontend/package.json ]]; then
  say "Building frontend"
  (cd frontend && npm ci && npm run build)
  SA="stweb$SUFFIX"
  say "Ensuring Storage account: $SA"
  set +e
  az storage account show -g "$RG" -n "$SA" >/dev/null 2>&1
  exists=$?
  set -e
  if [[ $exists -ne 0 ]]; then
    az storage account create -g "$RG" -n "$SA" -l "$LOC" --sku Standard_LRS >/dev/null
  fi
  az storage blob service-properties update --account-name "$SA" --static-website --index-document index.html --404-document index.html >/dev/null
  az storage blob upload-batch --account-name "$SA" -d '$web' -s frontend/dist >/dev/null
  FRONTEND_URL="https://$SA.z13.web.core.windows.net"
  say "Frontend published: $FRONTEND_URL"
else
  warn "frontend/ not found; skipping static website publish"
fi

# ===== 4) CORS update via Key Vault =====
say "Updating CORS origins in Key Vault"
CURRENT_CORS=$(az keyvault secret show --vault-name "$KV" --name BACKEND-CORS-ORIGINS --query value -o tsv 2>/dev/null || echo "")
python3 - "$CURRENT_CORS" "$FRONTEND_URL" <<'PY' 2>/dev/null | {
import os, sys
current = (sys.argv[1] or "").split(",") if len(sys.argv) > 1 else []
frontend = sys.argv[2] if len(sys.argv) > 2 else ""
items = set(x.strip() for x in current if x.strip())
items.add("http://localhost:5173")
items.add("https://localhost:5173")
if frontend:
    items.add(frontend)
print(",".join(sorted(items)))
PY
} | {
  read -r NEW_CORS
  if [[ -n "$NEW_CORS" ]]; then
    az keyvault secret set --vault-name "$KV" --name BACKEND-CORS-ORIGINS --value "$NEW_CORS" >/dev/null
    say "CORS updated: $NEW_CORS"
  else
    warn "Computed empty CORS; skipping update"
  fi
}

say "Restarting backend Container App to apply config"
az containerapp restart -g "$RG" -n "$CA_NAME" >/dev/null || warn "Restart failed"
sleep 5

# Recompute API_URL in case
API_FQDN=$(az containerapp show -g "$RG" -n "$CA_NAME" --query properties.configuration.ingress.fqdn -o tsv)
API_URL="https://$API_FQDN"

# ===== 5) Verify E2E =====
say "Verifying backend health"
LIVE_CODE=$(curl -sk -o /dev/null -w "%{http_code}" "$API_URL/api/v1/health/live")
READY_CODE=$(curl -sk -o /dev/null -w "%{http_code}" "$API_URL/api/v1/health/ready")

CORS_OK="skipped"
FINAL_CORS=$(az keyvault secret show --vault-name "$KV" --name BACKEND-CORS-ORIGINS --query value -o tsv 2>/dev/null || echo "")
if [[ -n "$FRONTEND_URL" ]]; then
  say "Probing CORS from origin: $FRONTEND_URL"
  HDRS=$(mktemp)
  curl -sk -D "$HDRS" -o /dev/null -H "Origin: $FRONTEND_URL" "$API_URL/api/v1/health/ready" || true
  if grep -i "^access-control-allow-origin:" "$HDRS" >/dev/null; then
    CORS_OK="yes"
  else
    CORS_OK="no"
  fi
  rm -f "$HDRS"
fi

HEALTH_OK="no"
if [[ "$LIVE_CODE" == "200" && "$READY_CODE" == "200" ]]; then
  HEALTH_OK="yes"
fi

echo
echo "==================== SUMMARY ===================="
echo "Backend URL:              $API_URL"
echo "Frontend URL:             ${FRONTEND_URL:-<not set>}"
echo "Final CORS (KV):          $FINAL_CORS"
echo "Migrations:               $MIGRATION_STATUS via ${MIGRATION_STRATEGY:-n/a}"
echo "Health live/ready ok:     $HEALTH_OK"
echo "CORS probe ok:            $CORS_OK"
echo "================================================="
echo

[[ "$HEALTH_OK" == "yes" ]] || die "Health checks failed"

say "Azure staging edges completed."

# EOF


