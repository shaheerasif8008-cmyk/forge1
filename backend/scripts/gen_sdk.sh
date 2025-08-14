#!/usr/bin/env bash
set -euo pipefail

# Generate TypeScript and Python SDKs from FastAPI OpenAPI schema and run golden tests.

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
OUT_DIR_TS="$ROOT_DIR/../sdk/ts"
OUT_DIR_PY="$ROOT_DIR/../sdk/py"

mkdir -p "$OUT_DIR_TS" "$OUT_DIR_PY"

API_URL=${API_URL:-"http://localhost:8000/api/v1/openapi.json"}

echo "Fetching OpenAPI spec from $API_URL" >&2
curl -sS "$API_URL" -o "$ROOT_DIR/openapi.json"

echo "Generating TypeScript SDK" >&2
npx --yes openapi-typescript "$ROOT_DIR/openapi.json" -o "$OUT_DIR_TS/index.d.ts"

echo "Generating Python SDK (pydantic models)" >&2
python - <<'PY'
import json, sys, os
spec = json.load(open(os.path.join(sys.argv[1], 'openapi.json')))
out = os.path.join(sys.argv[2], 'models.py')
with open(out, 'w') as f:
    f.write('# Auto-generated minimal SDK placeholder for models\nfrom typing import Any\n')
    f.write('OpenAPI: dict[str, Any] = ' + json.dumps(spec))
PY
"$ROOT_DIR" "$OUT_DIR_PY"

echo "Running golden tests" >&2
if [ -d "$ROOT_DIR/../sdk/tests" ]; then
  pytest -q "$ROOT_DIR/../sdk/tests"
fi

echo "Done."


