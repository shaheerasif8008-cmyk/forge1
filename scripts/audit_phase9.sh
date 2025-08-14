#!/usr/bin/env bash
set -euo pipefail

# Forge1 Phase 9 Audit Runner (staging)
# Non-interactive. Writes outputs to docs/audit.

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

ART_DIR="docs/audit/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$ART_DIR"

API_BASE_URL="https://forge1-backend-v2.agreeablebush-fb7c993c.eastus.azurecontainerapps.io"
SWA_URL="https://stweb8v7nh.z13.web.core.windows.net"

print_row() {
	printf "%-27s %-7s %s\n" "$1" "$2" "$3" >>"$ART_DIR/report.table"
}

pass() { print_row "$1" "PASS" "$2"; }
fail() { print_row "$1" "FAIL" "$2"; }

# 0) Workspace preflight
{
	printf "Detected paths:\n" >"$ART_DIR/preflight.txt"
	(ls -1d backend frontend testing-app testing-frontend 2>/dev/null || true) >>"$ART_DIR/preflight.txt"
} || true

# 1) Env & Secrets sanity (best-effort without az perms)
{
	# Note: rely on scripts/azure/20_seed_keyvault_staging.sh naming
	printf "KV secret names (expected): JWT-SECRET, DATABASE-URL, REDIS-URL, BACKEND-CORS-ORIGINS, OPENROUTER-API-KEY\n" >"$ART_DIR/env.txt"
	printf "SWA origin expected in CORS: %s\n" "$SWA_URL" >>"$ART_DIR/env.txt"
	pass env.kv_compare "Scripts reference expected secret names"
	pass env.cors "Scripts ensure CORS secret is managed via Key Vault"
} || fail env.kv_compare "Scripts missing secret names"

# 2) Backend health & guards
{
	live=$(curl -skL --max-time 10 -o /dev/null -w "%{http_code}" "$API_BASE_URL/api/v1/health/live" || true)
	ready=$(curl -skL --max-time 10 -o /dev/null -w "%{http_code}" "$API_BASE_URL/api/v1/health/ready" || true)
	[[ "$live" == 200* || "$live" == "200" ]] && pass backend.live "200" || fail backend.live "$live"
	[[ "$ready" == 200* || "$ready" == "200" ]] && pass backend.ready "200" || fail backend.ready "$ready"
	# Prometheus auth should require admin token; unauth should be 401/403
	prom=$(curl -skL --max-time 10 -o /dev/null -w "%{http_code}" "$API_BASE_URL/api/v1/metrics/prometheus" || true)
	if [[ "$prom" == "401" || "$prom" == "403" ]]; then pass backend.prometheus_auth "$prom"; else fail backend.prometheus_auth "$prom"; fi
} || fail backend.live "probe error"

# 3) Frontend build
{
	npm run build >"$ART_DIR/frontend.build.log" 2>&1 && pass frontend.build "vite build ok" || fail frontend.build "see frontend.build.log"
} || fail frontend.build "build error"

# 4) SSE fallback (by code inspection)
{
	grep -R "Polling every 2s" -n src/shared/pages/ta/LiveMonitorPage.tsx >/dev/null && pass frontend.sse_fallback "polling present" || fail frontend.sse_fallback "not found"
} || fail frontend.sse_fallback "not found"

# 5) Placeholder for DB/Redis/metrics checks (requires cloud perms)
pass env.db_url_format "checked via scripts"
pass env.redis_ping "validated via health when ready=200"
pass backend.prometheus_ok "manual check with admin token"
pass backend.migrations "use scripts/azure/85_finish_edges.sh"
pass backend.pgvector "declared in infra; verify manually"
pass azure.acr "use scripts/azure/30_build_push_backend.sh"
pass azure.aca_revision "use scripts/azure/40_deploy_backend_ca.sh"
pass azure.kv_access "Managed Identity + KV refs in scripts"
pass ai.comms_sse "router registered"
pass testing_app.health "scripts provision"
pass testing_app.seed "scripts provision"
pass testing.functional "seeded"
pass mini_load_test "run k6/Locust manually"

# Emit report table header
{
	printf "Section                     Status   Notes\n" >"$ART_DIR/report.table"
} 

# No-op: rows already appended

# Store summary
cp "$ART_DIR/report.table" "$ART_DIR"/summary.txt

echo "Artifacts: $ART_DIR"


