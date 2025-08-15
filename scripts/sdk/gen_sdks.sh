#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
API_URL=${API_URL:-"http://localhost:8000/openapi.json"}
SPEC_DIR="$ROOT_DIR/artifacts"
OUT_TS="$ROOT_DIR/sdks/typescript"
OUT_PY="$ROOT_DIR/sdks/python"

mkdir -p "$SPEC_DIR" "$OUT_TS" "$OUT_PY"

echo "Fetching OpenAPI spec from $API_URL" >&2
curl -sS "$API_URL" -o "$SPEC_DIR/openapi.json"

echo "Generating TypeScript SDK (ESM)" >&2
npx --yes @openapitools/openapi-generator-cli generate \
  -i "$SPEC_DIR/openapi.json" -g typescript-fetch \
  -o "$OUT_TS" \
  --additional-properties=supportsES6=true,typescriptThreePlus=true,npmName=@forge1/sdk,modelPropertyNaming=original

echo "Generating Python SDK" >&2
npx --yes @openapitools/openapi-generator-cli generate \
  -i "$SPEC_DIR/openapi.json" -g python \
  -o "$OUT_PY" \
  --additional-properties=packageName=forge1_sdk,projectName=forge1-sdk

echo "Done. Outputs in sdks/typescript and sdks/python" >&2


