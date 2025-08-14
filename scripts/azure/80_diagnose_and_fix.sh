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

# ===== Inputs / Flags =====
FRONTEND_URL="${FRONTEND_URL:-}"   # optional, if provided we’ll ensure CORS; if empty we can auto-host
AUTO_HOST="${AUTO_HOST:-true}"     # if true and FRONTEND_URL empty, publish a temp static site
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}" # run alembic upgrade head if DB reachable

# ===== Preconditions =====
need az; need jq || true
test -f .azure/env.staging || die ".azure/env.staging not found. Run 10_bootstrap_core.sh first."
# shellcheck disable=SC1091
source .azure/env.staging

say "Validating Azure login and subscription"
az account show >/dev/null 2>&1 || die "Run: az login"
: "${RG:?missing RG}"; : "${LOC:?missing LOC}"; : "${KV:?missing KV}"; : "${ACR:?missing ACR}"

# ===== Resource Checks =====
say "Verifying core resources exist"
az group show -n "$RG" >/dev/null || die "Resource group $RG not found"
az acr show -g "$RG" -n "$ACR" >/dev/null || die "ACR $ACR not found"
az keyvault show -g "$RG" -n "$KV" >/dev/null || die "Key Vault $KV not found"

# Container App env can be missing if named differently; non-fatal
if [[ -n "${ACA_ENV:-}" ]]; then
  az containerapp env show -g "$RG" -n "$ACA_ENV" >/dev/null || warn "Container Apps env $ACA_ENV not found (continuing)"
fi

# ===== Secrets & Config =====
say "Checking required Key Vault secrets"
required=(DATABASE-URL REDIS-URL JWT-SECRET BACKEND-CORS-ORIGINS OPENROUTER-API-KEY)
missing=()
for s in "${required[@]}"; do
  if ! az keyvault secret show --vault-name "$KV" --name "$s" --query value -o tsv >/dev/null 2>&1; then
    missing+=("$s")
  fi
done
if ((${#missing[@]})); then
  warn "Missing KV secrets: ${missing[*]}"
  die "Seed missing secrets, then re-run. (Use 16_create_datastores_and_seed_kv.sh and 20_seed_keyvault_staging.sh)"
fi

DB_URL=$(az keyvault secret show --vault-name "$KV" --name DATABASE-URL --query value -o tsv)
REDIS_URL=$(az keyvault secret show --vault-name "$KV" --name REDIS-URL --query value -o tsv)
CORS_VAL=$(az keyvault secret show --vault-name "$KV" --name BACKEND-CORS-ORIGINS --query value -o tsv)

# ===== Backend (Container App) =====
say "Ensuring backend Container App exists/healthy"
CA_NAME="forge1-backend"
if ! az containerapp show -g "$RG" -n "$CA_NAME" >/dev/null 2>&1; then
  die "Container App $CA_NAME not found. Run 70_finish_staging.sh first."
fi

FQDN=$(az containerapp show -g "$RG" -n "$CA_NAME" --query properties.configuration.ingress.fqdn -o tsv)
API_URL="https://$FQDN"
say "Backend URL: $API_URL"

# Health
say "Health checks"
LIVE=$(curl -sk -m 10 "$API_URL/api/v1/health/live" || true)
READY=$(curl -sk -m 15 "$API_URL/api/v1/health/ready" || true)
echo "LIVE => $LIVE"
echo "READY => $READY"

# If not ready, poke logs and suggest restart
if [[ "$READY" != *"ready"* ]]; then
  warn "Backend not ready. Fetching last logs…"
  az containerapp logs show -g "$RG" -n "$CA_NAME" --tail 200 || true
  warn "Attempting restart"
  az containerapp restart -g "$RG" -n "$CA_NAME" || true
  sleep 5
  READY=$(curl -sk -m 15 "$API_URL/api/v1/health/ready" || true)
  echo "READY(after restart) => $READY"
fi

# ===== Database diagnostics =====
say "Database connectivity & pgvector"
if command -v psql >/dev/null; then
  # shellcheck disable=SC2046
  HOST=$(echo "$DB_URL" | sed -E 's#.*@([^:/?]+).*#\1#')
  DBNAME=$(echo "$DB_URL" | sed -E 's#.*/([^/?]+)\?.*#\1#')
  # Try a trivial query and vector check
  PGPASSWORD="$(echo "$DB_URL" | sed -E 's#.*//[^:]+:([^@]+)@.*#\1#; s/%40/@/g; s/%3A/:/g')" \
  psql "host=$HOST port=5432 dbname=$DBNAME user=$(echo "$DB_URL" | sed -E 's#.*//([^:]+):.*#\1#') sslmode=require" \
    -tc "SELECT 1; CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null || warn "psql connectivity or pgvector enable failed (non-fatal)"
else
  warn "psql not installed; skipping DB ping"
fi

# Alembic migrations (optional)
if [[ "${RUN_MIGRATIONS}" == "true" ]]; then
  say "Running Alembic migrations"
  export DATABASE_URL="$DB_URL"
  if [[ -d backend && -f backend/alembic.ini ]]; then
    # Build alembic command
    if command -v alembic >/dev/null; then
      ALEMBIC_CMD=(alembic -c alembic.ini upgrade head)
    elif command -v python3 >/dev/null; then
      ALEMBIC_CMD=(python3 -m alembic -c alembic.ini upgrade head)
    elif command -v python >/dev/null; then
      ALEMBIC_CMD=(python -m alembic -c alembic.ini upgrade head)
    else
      die "Alembic not available"
    fi

    set +e
    (
      cd backend && "${ALEMBIC_CMD[@]}"
    )
    MIG_RC=$?
    set -e

    if [[ $MIG_RC -ne 0 ]]; then
      warn "Alembic failed with current driver; trying asyncpg fallback"
      ASYNC_URL=$(python3 - <<'PY'
import os, re
u=os.environ.get('DATABASE_URL','')
if '+asyncpg' in u:
    print(u)
else:
    u = re.sub(r"\+psycopg2\b", "+asyncpg", u)
    u = re.sub(r"\+psycopg\b", "+asyncpg", u)
    if u.startswith('postgresql://'):
        u = u.replace('postgresql://','postgresql+asyncpg://',1)
    print(u)
PY
)
      export DATABASE_URL="$ASYNC_URL"
      if command -v python3 >/dev/null; then
        python3 -m pip show asyncpg >/dev/null 2>&1 || python3 -m pip install --user --quiet asyncpg || true
      fi
      set +e
      (
        cd backend && "${ALEMBIC_CMD[@]}"
      )
      MIG_RC2=$?
      set -e
      if [[ $MIG_RC2 -ne 0 ]]; then
        warn "Alembic failed even with asyncpg fallback; skipping migrations (non-fatal). Use a venv and 'pip install -r backend/requirements.txt' to enable migrations."
      fi
    fi
  else
    warn "backend/alembic.ini not found; skipping migrations"
  fi
fi

# ===== Redis sanity =====
say "Redis sanity"
# Just validate URL format and that the instance exists
REDIS_HOST=$(echo "$REDIS_URL" | sed -E 's#.*@([^:/]+):.*#\1#')
az redis show -g "$RG" -n "$(echo "$REDIS_HOST" | cut -d. -f1)" >/dev/null || warn "Redis instance not visible via az (check name/region)"

# ===== ACR / Image sanity =====
say "ACR image sanity"
ACR_LOGIN=$(az acr show -g "$RG" -n "$ACR" --query loginServer -o tsv)
if ! az acr repository show -n "$ACR_LOGIN" --repository forge1-backend >/dev/null 2>&1; then
  warn "ACR repository forge1-backend not found; listing repos:"
  az acr repository list -n "$ACR_LOGIN" -o table || true
else
  say "forge1-backend tags:"
  az acr repository show-tags -n "$ACR_LOGIN" --repository forge1-backend -o table || true
fi

# ===== CORS update (if FRONTEND_URL provided or auto-host enabled) =====
NEED_RESTART=0
if [[ -n "$FRONTEND_URL" ]]; then
  say "Ensuring CORS includes FRONTEND_URL=$FRONTEND_URL"
  NEW_CORS=$(python3 - <<PY
v=set(map(str.strip,"""$CORS_VAL""".split(",")))
v.add("$FRONTEND_URL")
print(",".join(sorted(x for x in v if x)))
PY
)
  if [[ "$NEW_CORS" != "$CORS_VAL" ]]; then
    az keyvault secret set --vault-name "$KV" --name BACKEND-CORS-ORIGINS --value "$NEW_CORS" >/dev/null
    CORS_VAL="$NEW_CORS"
    NEED_RESTART=1
  fi
elif [[ "${AUTO_HOST}" == "true" ]]; then
  # Publish a temporary static site on Azure Storage if not already done
  SA="stweb$SUFFIX"
  say "Auto-hosting frontend (if bucket missing) to get a stable URL"
  AUTO_HOST_ERR=0
  if ! az storage account show -g "$RG" -n "$SA" >/dev/null 2>&1; then
    az storage account create -g "$RG" -n "$SA" -l "$LOC" --sku Standard_LRS >/dev/null 2>&1 || AUTO_HOST_ERR=1
    if [[ $AUTO_HOST_ERR -eq 0 ]]; then
      az storage blob service-properties update --account-name "$SA" --static-website --index-document index.html --404-document index.html >/dev/null 2>&1 || AUTO_HOST_ERR=1
    fi
  fi
  # Ensure a build exists
  if [[ $AUTO_HOST_ERR -eq 0 && -d frontend && -f frontend/package.json ]]; then
    (cd frontend && npm ci && npm run build) || AUTO_HOST_ERR=1
    if [[ $AUTO_HOST_ERR -eq 0 ]]; then
      az storage blob upload-batch --account-name "$SA" -d '$web' -s frontend/dist >/dev/null 2>&1 || AUTO_HOST_ERR=1
    fi
    FRONTEND_URL="https://$SA.z13.web.core.windows.net"
    NEW_CORS=$(python3 - <<PY
v=set(map(str.strip,"""$CORS_VAL""".split(",")))
v.add("$FRONTEND_URL")
print(",".join(sorted(x for x in v if x)))
PY
)
    if [[ $AUTO_HOST_ERR -eq 0 && "$NEW_CORS" != "$CORS_VAL" ]]; then
      az keyvault secret set --vault-name "$KV" --name BACKEND-CORS-ORIGINS --value "$NEW_CORS" >/dev/null 2>&1 || AUTO_HOST_ERR=1
      if [[ $AUTO_HOST_ERR -eq 0 ]]; then
        CORS_VAL="$NEW_CORS"
        NEED_RESTART=1
      fi
    fi
  else
    warn "Auto-host failed or frontend/ not found; skipping (non-fatal)"
  fi
fi

# ===== Restart if config changed =====
if [[ $NEED_RESTART -eq 1 ]]; then
  say "Restarting backend to apply updated CORS"
  az containerapp restart -g "$RG" -n "$CA_NAME" >/dev/null || warn "Restart failed"
  sleep 5
fi

# ===== Prometheus / metrics sanity (optional endpoints) =====
say "Metrics endpoint check (if exposed)"
curl -sk -m 10 "$API_URL/api/v1/metrics/prometheus" | head -n 3 || warn "Prom endpoint not accessible (ok if gated)"

# ===== Final live checks =====
say "Final health"
LIVE=$(curl -sk -m 10 "$API_URL/api/v1/health/live" || true)
READY=$(curl -sk -m 15 "$API_URL/api/v1/health/ready" || true)
STATUS_OK=1
[[ "$LIVE" == *"live"* ]] || STATUS_OK=0
[[ "$READY" == *"ready"* ]] || STATUS_OK=0

# ===== Summary =====
echo
echo "==================== SUMMARY ===================="
echo "Backend URL:              $API_URL"
echo "Frontend URL:             ${FRONTEND_URL:-<not set>}"
echo "KV BACKEND-CORS-ORIGINS:  $CORS_VAL"
echo "DB URL present:           $(test -n "$DB_URL" && echo yes || echo no)"
echo "Redis URL present:        $(test -n "$REDIS_URL" && echo yes || echo no)"
echo "Health live/ready ok:     $(test $STATUS_OK -eq 1 && echo yes || echo no)"
echo "================================================="
echo

if [[ $STATUS_OK -ne 1 ]]; then
  die "Health did not pass. Scroll logs above; fix and re-run."
else
  say "All green. Azure migration looks good."
  exit 0
fi

# EOF


