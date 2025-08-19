#!/usr/bin/env bash
set -euo pipefail

API="http://127.0.0.1:8000/api/v1"

echo "== Forge1 E2E Employee Demo =="

echo "1) Login (dev user via legacy form login)"
TOKEN=$(curl -sS -X POST "$API/auth/login" -H 'content-type: application/x-www-form-urlencoded' \
  --data 'username=admin@forge1.com&password=admin' | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')
if [[ -z "$TOKEN" ]]; then echo "Login failed"; exit 2; fi
echo "TOKEN: ${TOKEN:0:16}..."

HDR=( -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' )

TENANT_ID=$(curl -sS "$API/auth/me" -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("tenant_id",""))')
echo "Tenant: $TENANT_ID"

echo "2) Create employee"
EMP_OUT=$(curl -sS -X POST "$API/employees/" "${HDR[@]}" --data '{"name":"Demo Agent","role_name":"researcher","description":"Research topics","tools":["api_caller"]}')
echo "$EMP_OUT"
EMP_ID=$(echo "$EMP_OUT" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')
if [[ -z "$EMP_ID" ]]; then echo "Employee create failed"; exit 2; fi
echo "EMP_ID: $EMP_ID"

echo "3) Run a task"
RUN_OUT=$(curl -sS -X POST "$API/employees/$EMP_ID/run" "${HDR[@]}" --data '{"task":"Fetch latest news headline from https://example.com and summarize.","iterations":1}')
echo "$RUN_OUT"

TRACE_ID=$(echo "$RUN_OUT" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("trace_id",""))' || true)

echo "4) Add memory note"
MEM_OUT=$(curl -sS -X POST "$API/employees/$EMP_ID/memory/add" "${HDR[@]}" --data '{"content":"Demo note about the task."}')
echo "$MEM_OUT"

echo "5) Search memory"
SEARCH_OUT=$(curl -sS "$API/employees/$EMP_ID/memory/search?q=demo" "${HDR[@]}")
echo "$SEARCH_OUT"

echo "6) List logs and pick last task id"
LOGS=$(curl -sS "$API/employees/$EMP_ID/logs?limit=1" "${HDR[@]}")
echo "$LOGS"
TASK_ID=$(echo "$LOGS" | python3 -c 'import sys,json;arr=json.load(sys.stdin);print(arr[0]["id"] if arr else "")')
echo "TASK_ID: $TASK_ID"

echo "7) Fetch task review/trace"
if [[ -n "$TASK_ID" ]]; then
  TRACE=$(curl -sS "$API/reviews/$TASK_ID" "${HDR[@]}")
  echo "$TRACE"
fi

echo "== DONE =="


