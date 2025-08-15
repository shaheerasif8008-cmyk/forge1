#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT_DIR=${OUT_DIR:-"$ROOT/artifacts/locust_$(date +%s)"}
mkdir -p "$OUT_DIR"

FORGE1_API_URL=${FORGE1_API_URL:-http://localhost:8000} \
FORGE1_EMAIL=${FORGE1_EMAIL:-demo@example.com} \
FORGE1_PASSWORD=${FORGE1_PASSWORD:-admin} \
locust -f "$ROOT/tests/load/locust/locustfile.py" --headless -u ${USERS:-100} -r ${SPAWN_RATE:-10} -t ${DURATION:-1m} --csv "$OUT_DIR/results"

echo "Results CSV in $OUT_DIR" >&2


