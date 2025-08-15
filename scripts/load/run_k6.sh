#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
SCENARIO=${1:-baseline}
OUT_DIR=${OUT_DIR:-"$ROOT/artifacts/k6_${SCENARIO}_$(date +%s)"}
mkdir -p "$OUT_DIR"

echo "Running k6 scenario: $SCENARIO" >&2
CMD=(k6 run "$ROOT/tests/load/k6/${SCENARIO}.js")
FORGE1_API_URL=${FORGE1_API_URL:-http://localhost:8000} \
FORGE1_EMAIL=${FORGE1_EMAIL:-demo@example.com} \
FORGE1_PASSWORD=${FORGE1_PASSWORD:-admin} \
OUTPUT_DIR="$OUT_DIR" \
"${CMD[@]}"

echo "Results: $OUT_DIR" >&2


