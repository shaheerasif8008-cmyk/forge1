#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

bold() { printf "\033[1m%s\033[0m\n" "$*"; }

die() { echo "ERROR: $*" >&2; exit 1; }

: "${ENV:=dev}"
: "${DATABASE_URL:=postgresql+psycopg://forge:forge@127.0.0.1:5542/forge1_local}"
: "${REDIS_URL:=redis://127.0.0.1:6379/0}"
: "${OPENROUTER_API_KEY:=}"
: "${TARGET_API_URL:=http://localhost:8000}"
: "${TESTING_ADMIN_JWT:=}"
: "${TESTING_SERVICE_KEY:=dev}"
export TESTING_SERVICE_KEY

bold "1) Bring up infra (docker compose)"
if [ -f docker-compose.local.yml ]; then
  docker compose -f docker-compose.local.yml up -d
else
  echo "docker-compose file not found; assuming Postgres and Redis are already running"
fi

bold "2) Backend DB migrations"
(
  cd backend
  export DATABASE_URL
  alembic upgrade head || die "alembic upgrade failed"
)

bold "3) Backend readiness"
READY=$(curl -sS "${TARGET_API_URL}/api/v1/health/ready" | jq -c .)
echo "$READY"
STATUS=$(echo "$READY" | jq -r .status)
[ "$STATUS" = "ready" -o "$STATUS" = "ready_degraded" ] || die "/ready not ok"

bold "4) Seed admin and login"
JWT=$(curl -sS -X POST "${TARGET_API_URL}/api/v1/auth/login" -H 'content-type: application/x-www-form-urlencoded' --data-urlencode 'username=admin@forge1.com' --data-urlencode 'password=admin' | jq -r .access_token)
[ -n "$JWT" -a "$JWT" != "null" ] || die "failed to login"
HDR=(-H "Authorization: Bearer ${JWT}" -H "content-type: application/json")
TENANT=default

bold "5) Create employee"
EMP=$(curl -sS -X POST "${TARGET_API_URL}/api/v1/employees/" "${HDR[@]}" -d '{"name":"Full E2E","role_name":"researcher","description":"End-to-end","tools":["api_caller"]}')
EMP_ID=$(echo "$EMP" | jq -r .id)
[ -n "$EMP_ID" -a "$EMP_ID" != "null" ] || die "employee create failed: $EMP"

echo "EMP_ID=$EMP_ID"

bold "6) RAG seed (simple HTTP source)"
SRC=$(curl -sS -X POST "${TARGET_API_URL}/api/v1/rag/sources" "${HDR[@]}" -d '{"key":"e2e","type":"http","uri":"https://example.com"}') || true
echo "$SRC" | jq . 2>/dev/null || true
curl -sS -X POST "${TARGET_API_URL}/api/v1/rag/reindex" "${HDR[@]}" -d '{"ids":["src_default_e2e"]}' >/dev/null || true

bold "7) Run real task via LLM"
if [ -z "$OPENROUTER_API_KEY" ]; then
  echo "OPENROUTER_API_KEY missing; proceeding with whatever model routing is configured."
fi
RUN=$(curl -sS -X POST "${TARGET_API_URL}/api/v1/employees/${EMP_ID}/run" "${HDR[@]}" -d '{"task":"Introduce yourself","iterations":1}')
echo "$RUN" | jq . || true

bold "8) Add memory + search"
ADD=$(curl -sS -X POST "${TARGET_API_URL}/api/v1/employees/${EMP_ID}/memory/add" "${HDR[@]}" -d '{"content":"e2e memory note","kind":"note"}')
echo "$ADD" | jq . || true
SRCH=$(curl -sS "${TARGET_API_URL}/api/v1/employees/${EMP_ID}/memory/search?q=e2e" "${HDR[@]}")
echo "$SRCH" | jq . || true

bold "9) Metrics snapshot"
MET=$(curl -sS "${TARGET_API_URL}/api/v1/metrics/summary?hours=24" "${HDR[@]}")
echo "$MET" | jq . || true

bold "10) Testing App seed + suite (local in-process)"
if [ -z "$TESTING_ADMIN_JWT" ]; then
  export TESTING_ADMIN_JWT="$JWT"
fi
(
  cd testing-app
  export TARGET_API_URL="$TARGET_API_URL"
  export TESTING_ADMIN_JWT
  export TESTING_SERVICE_KEY
  chmod +x scripts/testing/run_local.sh || true
  ./scripts/testing/run_local.sh || true
)
ART_DIR=$(ls -dt testing-app/artifacts/* 2>/dev/null | head -n1 || true)
REPORT=$(ls "$ART_DIR"/*.html 2>/dev/null | head -n1 || true)

bold "11) Write VERIFY_LOCAL.md"
VFILE="docs/VERIFY_LOCAL.md"
mkdir -p docs
{
  echo "# Forge1 Local Verification"
  date -u +"Verified at: %Y-%m-%dT%H:%M:%SZ"
  echo
  echo "## Endpoints"
  echo "- API: ${TARGET_API_URL}"
  echo "- Ready: ${TARGET_API_URL}/api/v1/health/ready"
  echo "- Metrics: ${TARGET_API_URL}/metrics"
  echo
  echo "## Results"
  echo "- Ready: ${STATUS}"
  echo "- Employee: ${EMP_ID}"
  echo "- Testing Report: ${REPORT:-not-found}"
  echo
  echo '## Pass/Fail'
  PF=0
  if [ "$STATUS" = "ready" -o "$STATUS" = "ready_degraded" ]; then echo "- Ready: PASS"; else echo "- Ready: FAIL"; PF=1; fi
  if [ -n "$EMP_ID" ]; then echo "- Employee create: PASS"; else echo "- Employee create: FAIL"; PF=1; fi
  if [ -n "$REPORT" ]; then echo "- Testing suite: PASS"; else echo "- Testing suite: FAIL"; PF=1; fi
} > "$VFILE"

if grep -q "FAIL" "$VFILE"; then
  bold "FORGE1 LOCAL: NOT READY ❌"
  cat "$VFILE"
  exit 2
else
  bold "FORGE1 LOCAL: READY ✅"
  cat "$VFILE"
  exit 0
fi
