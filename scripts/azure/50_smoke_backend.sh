#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Azure Ops Pack - Smoke Test Backend

Checks /api/v1/health/live and /api/v1/health/ready endpoints on the given URL.

Options:
  --url <https://FQDN>    Base URL to test (required)

Usage:
  bash scripts/azure/50_smoke_backend.sh --url https://<fqdn>
USAGE
}

BASE_URL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) BASE_URL="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$BASE_URL" ]]; then
  echo "ERROR: --url is required" >&2
  usage
  exit 1
fi

echo "Smoke testing: $BASE_URL"

set +e
code_live=$(curl -skL --max-time 10 -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/health/live")
code_ready=$(curl -skL --max-time 10 -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/health/ready")
set -e

echo "live:  $code_live"
echo "ready: $code_ready"

if [[ "$code_live" == "200" && "$code_ready" == "200" ]]; then
  echo "SMOKE OK"
  exit 0
else
  echo "SMOKE FAILED" >&2
  echo "---- Logs ----" >&2
  curl -skL --max-time 10 "$BASE_URL/api/v1/health" || true
  exit 1
fi

#!/usr/bin/env bash
set -euo pipefail

# Smoke test backend deployment
# Usage: bash scripts/azure/50_smoke_backend.sh --url https://<fqdn>

URL=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) URL="$2"; shift 2;;
    *) echo "Unknown arg: $1" >&2; exit 1;;
  esac
done

if [[ -z "$URL" ]]; then
  echo "--url is required (e.g., https://<fqdn>)" >&2
  exit 1
fi

echo "Checking $URL/api/v1/health/live"
curl -fsS "$URL/api/v1/health/live" | grep -q '"status":"live"'

echo "Checking $URL/api/v1/health/ready"
code=$(curl -s -o /dev/null -w "%{http_code}" "$URL/api/v1/health/ready")
if [[ "$code" != "200" ]]; then
  echo "Ready check failed with status $code" >&2
  exit 1
fi
echo "Smoke checks passed."


