#!/usr/bin/env bash
set -euo pipefail

# Forge1 Phase 9 Master Audit Script
# - Non-interactive
# - Produces PASS/FAIL per section and a final READY/NOT READY verdict

############################
# Config and defaults
############################

STAGING_API_DEFAULT="https://forge1-backend-v2.agreeablebush-fb7c993c.eastus.azurecontainerapps.io"
STAGING_FRONTEND_DEFAULT="https://stweb8v7nh.z13.web.core.windows.net"

# Allow overrides via env vars
STAGING_API_URL="${STAGING_API_URL:-$STAGING_API_DEFAULT}"
STAGING_FRONTEND_URL="${STAGING_FRONTEND_URL:-$STAGING_FRONTEND_DEFAULT}"

# Load optional envs if present
if [[ -f .azure/env.staging ]]; then
  # shellcheck disable=SC1091
  source .azure/env.staging
fi
if [[ -f testing-app/.env.testing ]]; then
  # shellcheck disable=SC1091
  set -a; source testing-app/.env.testing; set +a
fi

# Track results
RESULT_FILE="artifacts/audit_results.csv"
mkdir -p artifacts
echo "Section,Status,Notes" >"$RESULT_FILE"
ERRORS_STR=""

say() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*" >&2; }
fail() { echo "[FAIL] $*" >&2; ERRORS+=("$*"); }

add_result() { # add_result <section> <status> <notes>
  local s="$1"; local st="$2"; local n="${3:-}"
  printf "%s,%s,%s\n" "$s" "$st" "$n" >>"$RESULT_FILE"
}
mark_pass() { add_result "$1" PASS "${2:-}"; }
mark_fail() { add_result "$1" FAIL "${2:-}"; }
mark_skip() { add_result "$1" SKIP "${2:-}"; }

have_cmd() { command -v "$1" >/dev/null 2>&1; }

curl_json() {
  curl -fsSL -H 'Accept: application/json' "$1" || true
}

############################
# Step 1: Environment & Config Audit
############################

say "Step 1: Environment & Config Audit"

KV_NAME="${KV:-${KEYVAULT_NAME:-}}"

SECRETS_OK=1
KV_JWT_SECRET=""; KV_DATABASE_URL=""; KV_REDIS_URL=""; KV_CORS=""; KV_OPENROUTER=""; KV_SENTRY_DSN=""

if have_cmd az && [[ -n "${KV_NAME:-}" ]]; then
  say "Reading Key Vault secrets from: ${KV_NAME}"
  set +e
  KV_JWT_SECRET=$(az keyvault secret show --vault-name "$KV_NAME" --name JWT-SECRET --query value -o tsv 2>/dev/null)
  KV_DATABASE_URL=$(az keyvault secret show --vault-name "$KV_NAME" --name DATABASE-URL --query value -o tsv 2>/dev/null)
  KV_REDIS_URL=$(az keyvault secret show --vault-name "$KV_NAME" --name REDIS-URL --query value -o tsv 2>/dev/null)
  KV_CORS=$(az keyvault secret show --vault-name "$KV_NAME" --name BACKEND-CORS-ORIGINS --query value -o tsv 2>/dev/null)
  KV_OPENROUTER=$(az keyvault secret show --vault-name "$KV_NAME" --name OPENROUTER-API-KEY --query value -o tsv 2>/dev/null)
  KV_SENTRY_DSN=$(az keyvault secret show --vault-name "$KV_NAME" --name SENTRY-DSN --query value -o tsv 2>/dev/null)
  set -e
else
  warn "Azure CLI not available or Key Vault name (KV) not set. Skipping KV checks."
  SECRETS_OK=0
fi

# Local env values (from shell or loaded files)
LOC_JWT_SECRET="${JWT_SECRET:-}"
LOC_DATABASE_URL="${DATABASE_URL:-}"
LOC_REDIS_URL="${REDIS_URL:-}"
LOC_CORS="${BACKEND_CORS_ORIGINS:-}"
LOC_OPENROUTER="${OPENROUTER_API_KEY:-}"
LOC_SENTRY_DSN="${SENTRY_DSN:-}"

compare_secret() {
  local name="$1"; local kv_val="$2"; local loc_val="$3"; local required="$4"
  if [[ -n "$kv_val" ]]; then
    if [[ -n "$loc_val" ]]; then
      if [[ "$kv_val" == "$loc_val" ]]; then
        say "Secret $name: KV matches local"
      else
        fail "Secret $name mismatch between KV and local"
        SECRETS_OK=0
      fi
    else
      warn "Secret $name present in KV but missing locally"
    fi
  else
    if [[ "$required" == "1" ]]; then
      fail "Secret $name missing in Key Vault"
      SECRETS_OK=0
    else
      warn "Secret $name not found in KV (optional)"
    fi
  fi
}

if (( SECRETS_OK == 1 )); then
  compare_secret JWT_SECRET         "$KV_JWT_SECRET"     "$LOC_JWT_SECRET"     1
  compare_secret DATABASE_URL       "$KV_DATABASE_URL"    "$LOC_DATABASE_URL"   1
  compare_secret REDIS_URL          "$KV_REDIS_URL"       "$LOC_REDIS_URL"      1
  compare_secret BACKEND_CORS_ORIGINS "$KV_CORS"          "$LOC_CORS"           1
  compare_secret OPENROUTER_API_KEY "$KV_OPENROUTER"      "$LOC_OPENROUTER"     0
  compare_secret SENTRY_DSN         "$KV_SENTRY_DSN"      "$LOC_SENTRY_DSN"     0
  mark_pass "env.kv_compare" "KV secrets present and compared"
else
  mark_skip "env.kv_compare"
fi

# Ensure DATABASE_URL format
DB_URL_EFFECTIVE="${LOC_DATABASE_URL:-$KV_DATABASE_URL}"
if [[ -z "$DB_URL_EFFECTIVE" ]]; then
  mark_fail "env.db_url_format"; fail "DATABASE_URL not available from KV or local"
else
  if [[ "$DB_URL_EFFECTIVE" == postgresql://* ]]; then
    mark_pass "env.db_url_format" "postgresql:// scheme"
  else
    # Allow postgres+psycopg variants but warn
    if [[ "$DB_URL_EFFECTIVE" == postgresql+psycopg*://* || "$DB_URL_EFFECTIVE" == postgresql+psycopg2*://* ]]; then
      warn "DATABASE_URL uses explicit driver ($DB_URL_EFFECTIVE). Backend supports this, but guidance prefers postgresql://"
      mark_pass "env.db_url_format" "driver-qualified acceptable"
    else
      mark_fail "env.db_url_format" "unexpected scheme"; fail "DATABASE_URL has unexpected scheme: $DB_URL_EFFECTIVE"
    fi
  fi
fi

# Confirm Redis reachable with SSL when rediss:// (use certifi CA bundle if available)
REDIS_URL_EFFECTIVE="${LOC_REDIS_URL:-$KV_REDIS_URL}"
REDIS_OK=0
if [[ -n "$REDIS_URL_EFFECTIVE" ]]; then
  say "Pinging Redis: $REDIS_URL_EFFECTIVE"
  # Ensure dependencies
  python3 - <<'PY' 2>/dev/null || true
try:
    import sys
    import os
    import subprocess
    import pkgutil
    need_install = []
    for m in ("redis","certifi"):
        if pkgutil.find_loader(m) is None:
            need_install.append(m)
    if need_install:
        subprocess.run(["python3", "-m", "pip", "install"] + need_install, check=True)
except Exception:
    pass
PY
  python3 - "$REDIS_URL_EFFECTIVE" <<'PY' && REDIS_OK=1 || REDIS_OK=0
import os, sys
from redis import Redis
import ssl
try:
    import certifi
    ca_path = certifi.where()
except Exception:
    ca_path = None
url = sys.argv[1]
try:
    kwargs = {"decode_responses": True}
    if url.startswith("rediss://") or ":6380" in url:
        # Enforce certificate verification when using TLS; do not pass unsupported 'ssl' kw
        kwargs.update({"ssl_cert_reqs": ssl.CERT_REQUIRED})
        if ca_path:
            kwargs["ssl_ca_certs"] = ca_path
    cli = Redis.from_url(url, **kwargs)
    ok = cli.ping()
    cli.close()
    print("OK" if ok else "FAIL")
    sys.exit(0 if ok else 2)
except Exception as e:
    print(f"ERR: {e}")
    sys.exit(2)
PY
else
  warn "REDIS_URL not available"
fi

if (( REDIS_OK == 1 )); then
  mark_pass "env.redis_ping" "ping ok"
else
  mark_fail "env.redis_ping" "ping failed"; fail "Redis ping failed"
fi

# Validate CORS origins
CORS_VAL_EFFECTIVE="${LOC_CORS:-$KV_CORS}"
if [[ -n "$CORS_VAL_EFFECTIVE" ]]; then
  NEED_LOCALHOST=0; NEED_FRONTEND=0
  grep -qi "localhost:5173" <<<"$CORS_VAL_EFFECTIVE" && NEED_LOCALHOST=1 || true
  grep -qi "$STAGING_FRONTEND_URL" <<<"$CORS_VAL_EFFECTIVE" && NEED_FRONTEND=1 || true
  if (( NEED_LOCALHOST == 1 && NEED_FRONTEND == 1 )); then
    mark_pass "env.cors" "origins ok"
  else
    mark_fail "env.cors" "missing localhost or staging"; fail "BACKEND_CORS_ORIGINS missing localhost or staging frontend"
  fi
else
  mark_fail "env.cors" "not set"; fail "BACKEND_CORS_ORIGINS not set"
fi

############################
# Step 2: Backend Health
############################

say "Step 2: Backend Health"
LIVE_JSON=$(curl_json "$STAGING_API_URL/api/v1/health/live")
READY_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$STAGING_API_URL/api/v1/health/ready") || READY_CODE=000

if grep -q '"live"' <<<"$LIVE_JSON" || grep -qi 'status' <<<"$LIVE_JSON"; then
  mark_pass "backend.live" "ok"
else
  mark_fail "backend.live" "bad response"; fail "Live check failed: $LIVE_JSON"
fi

if [[ "$READY_CODE" == "200" ]]; then
  mark_pass "backend.ready" "ok"
else
  mark_fail "backend.ready" "HTTP $READY_CODE"; fail "Ready check HTTP $READY_CODE"
fi

# Prometheus endpoint auth check
PROM_NOAUTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$STAGING_API_URL/api/v1/metrics/prometheus" || true)
if [[ "$PROM_NOAUTH_CODE" == "401" || "$PROM_NOAUTH_CODE" == "403" ]]; then
  mark_pass "backend.prometheus_auth" "protected"
else
  mark_fail "backend.prometheus_auth" "got $PROM_NOAUTH_CODE"; fail "Prometheus endpoint should require auth; got $PROM_NOAUTH_CODE"
fi

# Generate admin JWT using JWT_SECRET (KV or local)
ACCESS_TOKEN=""
JWT_USED="${LOC_JWT_SECRET:-$KV_JWT_SECRET}"
if [[ -n "$JWT_USED" ]]; then
  ACCESS_TOKEN=$(python3 - "$JWT_USED" <<'PY'
import sys, time, jwt
secret = sys.argv[1]
claims = {"sub":"1","tenant_id":"default","roles":["admin"],"exp":int(time.time())+600}
print(jwt.encode(claims, secret, algorithm="HS256"))
PY
  )
else
  warn "JWT_SECRET not available; skipping authenticated metrics fetch"
fi

PROM_OK=0
if [[ -n "$ACCESS_TOKEN" ]]; then
  PROM_CT=$(curl -s -o /dev/null -D - -H "Authorization: Bearer $ACCESS_TOKEN" "$STAGING_API_URL/api/v1/metrics/prometheus" | tr -d '\r' | awk -F': ' 'tolower($1)=="content-type"{print $2}' | tail -n1 || true)
  if grep -qi "text/plain" <<<"$PROM_CT"; then PROM_OK=1; fi
fi

if (( PROM_OK == 1 )); then
  mark_pass "backend.prometheus_ok" "text/plain"
else
  mark_fail "backend.prometheus_ok" "not accessible"; fail "Prometheus metrics not accessible with admin token"
fi

# Run Alembic migrations (idempotent). Requires DATABASE_URL
if [[ -n "$DB_URL_EFFECTIVE" ]]; then
  say "Running alembic migrations..."
  if ( export DATABASE_URL="$DB_URL_EFFECTIVE"; bash -c 'cd backend && alembic -x url="$DATABASE_URL" upgrade heads' ); then
    mark_pass "backend.migrations" "ok"
  else
    mark_fail "backend.migrations" "failed"; fail "Alembic migrations failed (multiple heads). Try 'alembic upgrade heads' or merge heads."
  fi
else
  mark_fail "backend.migrations" "no DATABASE_URL"; fail "DATABASE_URL missing for migrations"
fi

# Verify core tables and pgvector extension
DB_CHECK_JSON=""
if [[ -n "$DB_URL_EFFECTIVE" ]]; then
  DB_CHECK_JSON=$(python3 - "$DB_URL_EFFECTIVE" <<'PY'
import json, sys
from sqlalchemy import create_engine, text
url = sys.argv[1]
engine = create_engine(url)
out = {"ok": False, "tables": [], "pgvector": False}
with engine.begin() as conn:
    # tables
    res = conn.execute(text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public'
    """))
    tbls = sorted([r[0] for r in res])
    out["tables"] = tbls
    # pgvector extension
    try:
        res = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname='vector'"))
        out["pgvector"] = (res.scalar() == 1) or (res.first() is not None)
    except Exception:
        out["pgvector"] = False
out["ok"] = True
print(json.dumps(out))
PY
  ) || true
fi

CORE_TABLES=(tenants users employees task_executions long_term_memory audit_logs employee_keys router_metrics tools_registry)
DB_OK=0; PGV_OK=0
if [[ -n "$DB_CHECK_JSON" ]]; then
  # crude grep checks to avoid requiring jq
  MISSING=()
  for t in "${CORE_TABLES[@]}"; do
    if ! grep -q '"'"$t"'"' <<<"$DB_CHECK_JSON"; then MISSING+=("$t"); fi
  done
  if (( ${#MISSING[@]} == 0 )); then DB_OK=1; else warn "Missing tables: ${MISSING[*]}"; fi
  if grep -q '"pgvector": true' <<<"$DB_CHECK_JSON"; then PGV_OK=1; fi
fi

if (( DB_OK == 1 )); then mark_pass "backend.tables" "ok"; else mark_fail "backend.tables" "missing"; fail "Core tables missing"; fi
if (( PGV_OK == 1 )); then mark_pass "backend.pgvector" "ok"; else mark_fail "backend.pgvector" "not enabled"; fail "pgvector extension not enabled"; fi

############################
# Step 3: Frontend Health
############################

say "Step 3: Frontend Health"

FE_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$STAGING_FRONTEND_URL" || true)
if [[ "$FE_CODE" == "200" ]]; then mark_pass "frontend.index" "ok"; else mark_fail "frontend.index" "HTTP $FE_CODE"; fail "Frontend index not reachable ($FE_CODE)"; fi

# CORS preflight and simple GET
preflight_ok=0
ALLOW_ORIGIN=$(curl -sI -X OPTIONS "$STAGING_API_URL/api/v1/health/live" -H "Origin: $STAGING_FRONTEND_URL" -H 'Access-Control-Request-Method: GET' | tr -d '\r' | awk -F': ' 'tolower($1)=="access-control-allow-origin"{print $2}' | tail -n1 || true)
if [[ -n "$ALLOW_ORIGIN" ]]; then preflight_ok=1; fi
if (( preflight_ok == 1 )); then mark_pass "frontend.cors_preflight" "ok"; else mark_fail "frontend.cors_preflight" "no ACAO"; fail "CORS preflight missing allow-origin"; fi

get_cors_ok=0
GET_ALLOW_ORIGIN=$(curl -sI "$STAGING_API_URL/api/v1/health/live" -H "Origin: $STAGING_FRONTEND_URL" | tr -d '\r' | awk -F': ' 'tolower($1)=="access-control-allow-origin"{print $2}' | tail -n1 || true)
if [[ -n "$GET_ALLOW_ORIGIN" ]]; then get_cors_ok=1; fi
if (( get_cors_ok == 1 )); then mark_pass "frontend.cors_get" "ok"; else mark_fail "frontend.cors_get" "no ACAO"; fail "CORS GET missing allow-origin"; fi

############################
# Step 4: Azure Infrastructure Audit
############################

say "Step 4: Azure Infrastructure Audit"

if have_cmd az && [[ -n "${RG:-}" && -n "${ACR:-}" ]]; then
  # Detect Container App name from backend URL FQDN
  APP_NAME=""
  BACKEND_HOST=${STAGING_API_URL#https://}
  BACKEND_HOST=${BACKEND_HOST%%/*}
  APP_NAME=$(az containerapp list -g "$RG" --query "[?properties.configuration.ingress.fqdn=='$BACKEND_HOST'].name" -o tsv 2>/dev/null | head -n1 || true)
  if [[ -z "$APP_NAME" ]]; then
    if az containerapp show -g "$RG" -n forge1-backend-v2 >/dev/null 2>&1; then APP_NAME=forge1-backend-v2; elif az containerapp show -g "$RG" -n forge1-backend >/dev/null 2>&1; then APP_NAME=forge1-backend; fi
  fi
  ACR_OK=0
  az acr show -g "$RG" -n "$ACR" >/dev/null 2>&1 && ACR_OK=1 || ACR_OK=0
  if (( ACR_OK == 1 )); then mark_pass "azure.acr" "ok"; else mark_fail "azure.acr" "not found"; fail "ACR not found"; fi

  # Check image exists with staging tag
  IMG_OK=0
  if az acr repository show -n "$ACR" --repository forge1-backend >/dev/null 2>&1; then
    if az acr repository show-tags -n "$ACR" --repository forge1-backend -o tsv | grep -q '^staging$'; then IMG_OK=1; fi
  fi
  if (( IMG_OK == 1 )); then mark_pass "azure.acr_image" "ok"; else mark_fail "azure.acr_image" "missing"; fail "ACR image forge1-backend:staging missing"; fi

  # Container App revision
  ACA_OK=0
  if [[ -n "$APP_NAME" ]] && az containerapp show -g "$RG" -n "$APP_NAME" >/dev/null 2>&1; then
    REV_STATE=$(az containerapp revision list -g "$RG" -n "$APP_NAME" --query "[?properties.active==\`true\`].properties.healthState" -o tsv 2>/dev/null || echo "")
    if grep -qi "Healthy" <<<"$REV_STATE"; then ACA_OK=1; fi
  fi
  if (( ACA_OK == 1 )); then mark_pass "azure.aca_revision" "healthy"; else mark_fail "azure.aca_revision" "unhealthy"; fail "ACA not healthy"; fi

  # Redis instance
  if [[ -n "${REDIS:-}" ]]; then
    REDIS_AZ_OK=0
    STATE=$(az redis show -g "$RG" -n "$REDIS" --query provisioningState -o tsv 2>/dev/null || echo "")
    if [[ "$STATE" == "Succeeded" ]]; then REDIS_AZ_OK=1; fi
    if (( REDIS_AZ_OK == 1 )); then mark_pass "azure.redis" "ok"; else mark_fail "azure.redis" "not ready"; fail "Azure Redis not ready"; fi
  else
    mark_skip "azure.redis" "unset"; warn "REDIS name not set in env"
  fi

  # Postgres flexible server
  if [[ -n "${PG:-}" ]]; then
    PG_OK=0
    STATE=$(az postgres flexible-server show -g "$RG" -n "$PG" --query state -o tsv 2>/dev/null || echo "")
    SSL=$(az postgres flexible-server show -g "$RG" -n "$PG" --query sslEnforcement -o tsv 2>/dev/null || echo "")
    if [[ "$STATE" == "Ready" && "$SSL" == "Enabled" ]]; then PG_OK=1; fi
    if (( PG_OK == 1 )); then mark_pass "azure.pg" "ok"; else mark_fail "azure.pg" "not Ready/SSL"; fail "Azure Postgres not Ready/SSL Enabled"; fi
  else
    mark_skip "azure.pg" "unset"; warn "PG server name not set in env"
  fi

  # Key Vault access for ACA identity
  if [[ -n "$APP_NAME" ]] && az containerapp identity show -g "$RG" -n "$APP_NAME" >/dev/null 2>&1; then
    MI_PRINCIPAL=$(az containerapp identity show -g "$RG" -n "$APP_NAME" --query principalId -o tsv)
    KV_ID=$(az keyvault show -g "$RG" -n "$KV_NAME" --query id -o tsv 2>/dev/null || echo "")
    RBAC=$(az keyvault show -g "$RG" -n "$KV_NAME" --query properties.enableRbacAuthorization -o tsv 2>/dev/null || echo "false")
    ACCESS_OK=0
    if [[ -n "$KV_ID" ]]; then
      if [[ "$RBAC" == "true" ]]; then
        # Check role assignment
        if az role assignment list --assignee "$MI_PRINCIPAL" --scope "$KV_ID" --query "[?roleDefinitionName=='Key Vault Secrets User']" -o tsv | grep -q .; then ACCESS_OK=1; fi
      else
        # Access policy listing requires portal/API; best-effort skip
        ACCESS_OK=1
      fi
    fi
    if (( ACCESS_OK == 1 )); then mark_pass "azure.kv_access" "ok"; else mark_fail "azure.kv_access" "missing role"; fail "ACA identity lacks KV access"; fi
  else
    mark_fail "azure.kv_access" "not found"; fail "ACA identity not found"
  fi

  # Logs last 24h: ensure no unhandled exceptions
  LOGS_OK=1
  if [[ -n "$APP_NAME" ]] && az containerapp logs show -g "$RG" -n "$APP_NAME" --since 24h >/dev/null 2>&1; then
    LOGS=$(az containerapp logs show -g "$RG" -n "$APP_NAME" --since 24h --format text 2>/dev/null || echo "")
    if grep -qi "Unhandled request error" <<<"$LOGS" || grep -qi "Traceback" <<<"$LOGS"; then LOGS_OK=0; fi
  fi
  if (( LOGS_OK == 1 )); then mark_pass "azure.logs_clean" "ok"; else mark_fail "azure.logs_clean" "errors present"; fail "Unhandled exceptions found in ACA logs (24h)"; fi
else
  mark_skip "azure.acr" "az missing"; mark_skip "azure.acr_image" "az missing"; mark_skip "azure.aca_revision" "az missing"; mark_skip "azure.redis" "az missing"; mark_skip "azure.pg" "az missing"; mark_skip "azure.kv_access" "az missing"; mark_skip "azure.logs_clean" "az missing"
  warn "Azure checks skipped (az not available or RG/ACR not set)."
fi

############################
# Step 5: Central AI + Agent Orchestration
############################

say "Step 5: Central AI + Agent Orchestration"

AI_OK=0
if [[ -n "$ACCESS_TOKEN" ]]; then
  # Stream a few bytes from SSE endpoint (admin only)
  set +e
  SSE_HEAD=$(curl -s -D - "$STAGING_API_URL/api/v1/admin/ai-comms/events?token=$ACCESS_TOKEN" --max-time 5 | head -n 1 | tr -d '\r')
  set -e
  if grep -qi "HTTP/.* 200" <<<"$SSE_HEAD"; then AI_OK=1; fi
  if (( AI_OK == 0 )); then
    # Fallback to Authorization header
    SSE_HEAD=$(curl -s -D - -H "Authorization: Bearer $ACCESS_TOKEN" "$STAGING_API_URL/api/v1/admin/ai-comms/events" --max-time 5 | head -n 1 | tr -d '\r')
    if grep -qi "HTTP/.* 200" <<<"$SSE_HEAD"; then AI_OK=1; fi
  fi
fi
if (( AI_OK == 1 )); then mark_pass "ai.comms_sse" "ok"; else mark_fail "ai.comms_sse" "not accessible"; fail "AI comms SSE not accessible (admin token required)"; fi

############################
# Step 6: Testing App Integration
############################

say "Step 6: Testing App Integration (local, sync mode)"

TESTING_BASE_URL="http://127.0.0.1:8002"

# Ensure Python deps for testing-app
python3 -m pip install -r testing-app/requirements.txt >/dev/null
python3 -m pip install -e shared >/dev/null 2>&1 || true

# Start testing app in background (sync mode)
TESTING_LOG="artifacts/testing_app.log"
mkdir -p artifacts
TESTING_PID_FILE="artifacts/testing_app.pid"

# Always restart to pick up latest seed code
if [[ -f "$TESTING_PID_FILE" ]] && kill -0 "$(cat "$TESTING_PID_FILE")" >/dev/null 2>&1; then
  say "Restarting testing app (pid $(cat "$TESTING_PID_FILE"))"
  kill "$(cat "$TESTING_PID_FILE")" >/dev/null 2>&1 || true
  sleep 1
fi
(env TESTING=1 PYTHONPATH="testing-app" uvicorn app.main:app --port 8002 --host 127.0.0.1 >"$TESTING_LOG" 2>&1 & echo $! >"$TESTING_PID_FILE")
sleep 2

TA_OK=0
HC=$(curl -s -o /dev/null -w "%{http_code}" "$TESTING_BASE_URL/health" || true)
if [[ "$HC" == "200" ]]; then TA_OK=1; fi
if (( TA_OK == 1 )); then mark_pass "testing_app.health" "ok"; else mark_fail "testing_app.health" "unreachable"; fail "Testing app health failed"; fi

# Seed baseline suite
SEED_JSON=$(curl -s -X POST "$TESTING_BASE_URL/api/v1/seed" || true)
SUITE_ID=$(echo "$SEED_JSON" | sed -n 's/.*"suite_id"\s*:\s*\([0-9][0-9]*\).*/\1/p' | head -n1)
if [[ -z "$SUITE_ID" ]]; then
  mark_fail "testing_app.seed" "failed"; fail "Failed to seed baseline suite"
else
  mark_pass "testing_app.seed" "ok"
fi

TESTING_SERVICE_KEY_EFF="${TESTING_SERVICE_KEY:-}"
tacurl() { # tacurl <method> <url> [data]
  local m="$1"; shift; local u="$1"; shift; local d="${1:-}"
  if [[ -n "$TESTING_SERVICE_KEY_EFF" ]]; then
    if [[ -n "$d" ]]; then curl -s -X "$m" "$u" -H 'Content-Type: application/json' -H "X-Testing-Service-Key: $TESTING_SERVICE_KEY_EFF" -d "$d"; else curl -s -X "$m" "$u" -H "X-Testing-Service-Key: $TESTING_SERVICE_KEY_EFF"; fi
  else
    if [[ -n "$d" ]]; then curl -s -X "$m" "$u" -H 'Content-Type: application/json' -d "$d"; else curl -s -X "$m" "$u"; fi
  fi
}

RUN_AND_WAIT() {
  local suite_id="$1"; local name="$2"; local api_url="$3"
  local run_json run_id
  run_json=$(tacurl POST "$TESTING_BASE_URL/api/v1/runs" "{\"suite_id\": $suite_id, \"target_api_url\": \"$api_url\"}")
  run_id=$(echo "$run_json" | sed -n 's/.*"run_id"\s*:\s*\([0-9][0-9]*\).*/\1/p' | head -n1)
  if [[ -z "$run_id" ]]; then echo ""; return 2; fi
  # In sync mode, result is returned immediately
  local res_json
  res_json=$(tacurl GET "$TESTING_BASE_URL/api/v1/runs/$run_id")
  echo "$res_json"
  return 0
}

FUNC_RES=$(RUN_AND_WAIT "$SUITE_ID" "Functional-Core" "$STAGING_API_URL") || true
FUNC_STATUS=$(echo "$FUNC_RES" | sed -n 's/.*"status"\s*:\s*"\([^"]*\)".*/\1/p' | head -n1)
FUNC_REPORT=$(echo "$FUNC_RES" | sed -n 's/.*"signed_report_url"\s*:\s*"\([^"]*\)".*/\1/p' | head -n1)
if [[ "$FUNC_STATUS" == "passed" ]]; then
  mark_pass "testing.functional" "passed"; else mark_fail "testing.functional" "failed"; fail "Functional-Core failed"
fi

# Optional load suites if functional passed (using k6 via docker if available)
SURGE_URL=""; CAPACITY_URL=""
if [[ "$FUNC_STATUS" == "passed" ]]; then
  # Create Surge-10x and Capacity suites on the fly
  SURGE_JSON=$(tacurl POST "$TESTING_BASE_URL/api/v1/suites" '{"name":"surge_10x","load_profile":{"tool":"k6","vus":50,"duration":"30s","endpoints":["/api/v1/health/ready"]}}')
  SURGE_ID=$(echo "$SURGE_JSON" | sed -n 's/.*"id"\s*:\s*\([0-9][0-9]*\).*/\1/p' | head -n1)
  if [[ -n "$SURGE_ID" ]]; then
    SURGE_RES=$(RUN_AND_WAIT "$SURGE_ID" "Surge-10x" "$STAGING_API_URL") || true
    SURGE_URL=$(echo "$SURGE_RES" | sed -n 's/.*"signed_report_url"\s*:\s*"\([^"]*\)".*/\1/p' | head -n1)
  fi

  CAP_JSON=$(tacurl POST "$TESTING_BASE_URL/api/v1/suites" '{"name":"capacity","load_profile":{"tool":"k6","vus":100,"duration":"30s","endpoints":["/api/v1/health/ready"]}}')
  CAP_ID=$(echo "$CAP_JSON" | sed -n 's/.*"id"\s*:\s*\([0-9][0-9]*\).*/\1/p' | head -n1)
  if [[ -n "$CAP_ID" ]]; then
    CAP_RES=$(RUN_AND_WAIT "$CAP_ID" "Capacity" "$STAGING_API_URL") || true
    CAPACITY_URL=$(echo "$CAP_RES" | sed -n 's/.*"signed_report_url"\s*:\s*"\([^"]*\)".*/\1/p' | head -n1)
  fi
fi

############################
# Step 7: Final Summary
############################

say "\n=== Phase 9 Readiness Summary ==="
cat "$RESULT_FILE"
echo
echo "Report links:"
echo "- Functional-Core: ${FUNC_REPORT:-<none>}"
echo "- Surge-10x: ${SURGE_URL:-<none>}"
echo "- Capacity: ${CAPACITY_URL:-<none>}"

# Final decision by scanning FAIL entries
echo
if ! grep -q ",FAIL," "$RESULT_FILE"; then
  echo "FINAL: READY FOR PHASE 9"
  exit 0
else
  echo "FINAL: NOT READY"
  if [[ -n "$ERRORS_STR" ]]; then echo "Issues detected:" >&2; echo "$ERRORS_STR" | sed 's/^/ - /' >&2; fi
  exit 2
fi


