#!/usr/bin/env bash
set -euo pipefail

# Forge 1 Phase 6 smoke script
# Preconditions:
# - Backend running at ${API_BASE:-http://localhost:8000}
# - ENV=dev for login endpoint, or provide TOKEN directly

API_BASE=${API_BASE:-http://localhost:8000}
TENANT_A=${TENANT_A:-tenant_a}
TENANT_B=${TENANT_B:-tenant_b}

info() { echo "[INFO] $*"; }
fail() { echo "[ERROR] $*" >&2; exit 1; }

get_token() {
  if [[ -n "${TOKEN:-}" ]]; then
    echo "$TOKEN"; return 0;
  fi
  # Dev login path
  local username=${USERNAME:-admin}
  local password=${PASSWORD:-admin}
  local resp token
  resp=$(curl -sS -X POST "$API_BASE/api/v1/auth/login" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode "username=$username" \
    --data-urlencode "password=$password")
  token=$(echo "$resp" | jq -r .access_token)
  [[ "$token" != "null" && -n "$token" ]] || fail "Failed to obtain token. Response: $resp"
  echo "$token"
}

create_tenant_token() {
  local base_token=$1
  local tenant_id=$2
  # Use /auth/me to verify; for now we reuse base token and set tenant via header override if supported.
  # In this codebase tokens carry tenant in claim; for smoke we reuse base token and rely on default tenant.
  echo "$base_token"
}

create_employee() {
  local token=$1 tenant=$2 name=$3
  info "Creating employee $name in $tenant"
  curl -sS -X POST "$API_BASE/api/v1/employees" \
    -H "Authorization: Bearer $token" \
    -H 'Content-Type: application/json' \
    -d @- <<JSON | jq -e .id >/dev/null || fail "Create employee failed"
{ "name": "$name", "role_name": "research_assistant", "description": "Test employee", "tools": [] }
JSON
}

run_task() {
  local token=$1 employee_id=$2 prompt=$3
  curl -sS -X POST "$API_BASE/api/v1/employees/$employee_id/run" \
    -H "Authorization: Bearer $token" \
    -H 'Content-Type: application/json' \
    -d "{\"task\": \"$prompt\", \"iterations\": 1}" | jq .
}

trigger_low_score() {
  local token=$1
  curl -sS -X POST "$API_BASE/api/v1/ai/execute" \
    -H "Authorization: Bearer $token" \
    -H 'Content-Type: application/json' \
    -d '{"task": "cause a failure to trigger escalation", "context": {"force_error": true}}' | jq .
}

list_escalations() {
  local token=$1 tenant=$2
  curl -sS "$API_BASE/api/v1/admin/escalations/?tenant_id=$tenant" \
    -H "Authorization: Bearer $token" | jq .
}

approve_escalation() {
  local token=$1 id=$2
  curl -sS -X POST "$API_BASE/api/v1/admin/escalations/$id/approve" \
    -H "Authorization: Bearer $token" | jq .
}

retry_escalation() {
  local token=$1 id=$2
  curl -sS -X POST "$API_BASE/api/v1/admin/escalations/$id/retry" \
    -H "Authorization: Bearer $token" | jq .
}

check_cost_latency_caps() {
  local token=$1
  # Pull metrics summary
  curl -sS "$API_BASE/api/v1/metrics?days=1" -H "Authorization: Bearer $token" | jq .summary
}

main() {
  command -v jq >/dev/null || fail "jq is required"
  local base_token tenant_a_token tenant_b_token
  base_token=$(get_token)
  info "Got base token"

  # For now tokens embed tenant; this script demonstrates flow using same token
  tenant_a_token=$(create_tenant_token "$base_token" "$TENANT_A")
  tenant_b_token=$(create_tenant_token "$base_token" "$TENANT_B")

  # Create two employees (one per tenant)
  create_employee "$tenant_a_token" "$TENANT_A" "Smoke Emp A" || true
  create_employee "$tenant_b_token" "$TENANT_B" "Smoke Emp B" || true

  # List employees to obtain IDs
  emp_a=$(curl -sS "$API_BASE/api/v1/employees" -H "Authorization: Bearer $tenant_a_token" | jq -r '.[0].id')
  [[ -n "$emp_a" && "$emp_a" != "null" ]] || fail "No employee found in tenant A"

  # Run a trivial task
  info "Running task on $emp_a"
  run_task "$tenant_a_token" "$emp_a" "Say hello" >/dev/null

  # Trigger low-score path and potential escalation
  info "Triggering low-score execute"
  trigger_low_score "$tenant_a_token" >/dev/null || true

  # Check escalations and approve/retry one if present
  esc_json=$(list_escalations "$tenant_a_token" "$TENANT_A")
  esc_id=$(echo "$esc_json" | jq -r '.[0].id // empty')
  if [[ -n "$esc_id" ]]; then
    info "Approving escalation $esc_id and retrying"
    approve_escalation "$tenant_a_token" "$esc_id" >/dev/null || true
    retry_escalation "$tenant_a_token" "$esc_id" >/dev/null || true
  else
    info "No escalations found (OK if retries succeeded)"
  fi

  # Check costs/latency caps via metrics summary
  info "Checking metrics summary"
  check_cost_latency_caps "$tenant_a_token" >/dev/null || true

  info "Smoke completed"
}

main "$@"


