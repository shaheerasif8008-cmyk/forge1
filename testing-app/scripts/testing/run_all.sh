#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-"http://localhost:8002"}
API=${API:-"$BASE_URL/api/v1"}
KEY_HDR=${KEY_HDR:-"X-Testing-Service-Key"}
KEY=${TESTING_SERVICE_KEY:-""}
TARGET_API_URL=${TARGET_API_URL:-"http://localhost:8000"}

echo "Seeding canonical suites..."
SEED=$(curl -s -X POST -H "$KEY_HDR: $KEY" "$API/seed")
echo "$SEED"

echo "Listing suites..."
SUITES=$(curl -s -H "$KEY_HDR: $KEY" "$API/suites")
echo "$SUITES" | jq -r '.[] | "\(.id)\t\(.name)"'

echo "Running all suites sequentially..."
for ID in $(echo "$SUITES" | jq -r '.[].id'); do
  echo "== Running suite $ID =="
  RES=$(curl -s -H "$KEY_HDR: $KEY" -H 'Content-Type: application/json' -d "{\"suite_id\": $ID, \"target_api_url\": \"$TARGET_API_URL\"}" "$API/runs")
  RID=$(echo "$RES" | jq -r '.run_id')
  sleep 1
  INFO=$(curl -s -H "$KEY_HDR: $KEY" "$API/runs/$RID")
  STATUS=$(echo "$INFO" | jq -r '.run.status')
  REPORT=$(echo "$INFO" | jq -r '.signed_report_url')
  echo "Run $RID status: $STATUS | Report: $BASE_URL$REPORT"
done


