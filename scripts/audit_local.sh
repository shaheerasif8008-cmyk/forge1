#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

echo "[1/5] Checking backend /api/v1/health..."
curl -sS "${API_BASE_URL}/api/v1/health" | jq . || curl -sS "${API_BASE_URL}/api/v1/health"

echo "[2/5] Checking backend readiness..."
curl -sS "${API_BASE_URL}/api/v1/health/ready" | jq . || curl -sS "${API_BASE_URL}/api/v1/health/ready"

echo "[3/5] Authenticating (demo login)..."
TOKEN=$(curl -sS -X POST -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin" \
  "${API_BASE_URL}/api/v1/auth/login" | jq -r .access_token || true)
if [[ -z "${TOKEN}" || "${TOKEN}" == "null" ]]; then
  echo "WARN: Could not obtain token. Make sure ENV=dev or local and demo user exists. Continuing unauthenticated for public endpoints."
else
  echo "Obtained token"
fi

auth_header=()
if [[ -n "${TOKEN:-}" && "${TOKEN}" != "null" ]]; then
  auth_header=(-H "Authorization: Bearer ${TOKEN}")
fi

echo "[4/5] Checking metrics summary/trends/activity..."
curl -sS "${auth_header[@]}" "${API_BASE_URL}/api/v1/metrics/summary?hours=24" | jq . || true
curl -sS "${auth_header[@]}" "${API_BASE_URL}/api/v1/metrics/trends?hours=6&bucket_minutes=30" | jq . || true
curl -sS "${auth_header[@]}" "${API_BASE_URL}/api/v1/metrics/activity?limit=10" | jq . || true

echo "[5/5] Checking frontend UI..."
code=$(
  curl -sS -o /dev/null -w "%{http_code}" "${FRONTEND_URL}"
)
echo "Frontend GET / => HTTP ${code}"
if [[ "${code}" != "200" && "${code}" != "304" ]]; then
  echo "WARN: Frontend may not be running at ${FRONTEND_URL}"
fi

echo "Done."


