#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-"http://localhost:8002"}
API=${API:-"$BASE_URL/api/v1"}
KEY_HDR=${KEY_HDR:-"X-Testing-Service-Key"}
KEY=${TESTING_SERVICE_KEY:-""}
SUITE_ARG=${1:-""}
shift || true
# Allow TARGET_API_URL=... as a positional arg
for ARG in "$@"; do
  case "$ARG" in
    TARGET_API_URL=*) export TARGET_API_URL="${ARG#*=}" ;;
  esac
done
TARGET_API_URL=${TARGET_API_URL:-"http://localhost:8000"}

if [ -z "$SUITE_ARG" ]; then
  echo "Usage: $0 <suite_id|suite_name> [TARGET_API_URL=http://...]" >&2
  exit 1
fi

SUITE_ID="$SUITE_ARG"
if ! printf '%s' "$SUITE_ARG" | grep -Eq '^[0-9]+$'; then
  # resolve name to id
  LIST=$(curl -s -H "$KEY_HDR: $KEY" "$API/suites")
  SUITE_ID=$(python3 - <<PY
import sys,json
name=sys.argv[1]
data=json.loads(sys.stdin.read() or '[]')
sid=None
for s in data:
    if str(s.get('name',''))==name:
        sid=s.get('id')
        break
print(sid or '')
PY
"$SUITE_ARG" <<<"$LIST")
fi

if [ -z "$SUITE_ID" ]; then
  echo "Suite not found: $SUITE_ARG" >&2
  exit 2
fi

echo "Creating run for suite $SUITE_ID (target=$TARGET_API_URL) ..."
RUN_JSON=$(curl -s -H "$KEY_HDR: $KEY" -H 'Content-Type: application/json' \
  -d "{\"suite_id\": $SUITE_ID, \"target_api_url\": \"$TARGET_API_URL\"}" \
  "$API/runs")
echo "$RUN_JSON"
RUN_ID=$(echo "$RUN_JSON" | jq -r '.run_id')
if [ "$RUN_ID" = "null" ] || [ -z "$RUN_ID" ]; then
  echo "Failed to create run" >&2
  exit 2
fi

echo "Fetching run status ..."
RUN_RES=$(curl -s -H "$KEY_HDR: $KEY" "$API/runs/$RUN_ID")
STATUS=$(echo "$RUN_RES" | jq -r '.run.status')
REPORT=$(echo "$RUN_RES" | jq -r '.signed_report_url')
echo "Status: $STATUS"
echo "Signed Report: $BASE_URL$REPORT"


