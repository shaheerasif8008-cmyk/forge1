#!/usr/bin/env bash
set -euo pipefail

# Defaults
export TESTING=1
export TESTING_SERVICE_KEY=${TESTING_SERVICE_KEY:-dev}
export TESTING_TARGET_API_URL_DEFAULT=${TESTING_TARGET_API_URL_DEFAULT:-http://localhost:8000}

APP_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$APP_ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -U pip >/dev/null
pip install -r requirements.txt >/dev/null
pip install -e ../shared >/dev/null || true

# Run seed and a quick run using the FastAPI app (in-process)
python - <<'PY'
from fastapi.testclient import TestClient
from app.main import create_app
import os
app = create_app()
client = TestClient(app)
headers = {"X-Testing-Service-Key": os.getenv("TESTING_SERVICE_KEY", "")}
r = client.post("/api/v1/seed", headers=headers)
assert r.status_code == 200, r.text
suite_id = r.json()["suite_id"]
r2 = client.post("/api/v1/runs", json={"suite_id": suite_id, "target_api_url": os.getenv("TESTING_TARGET_API_URL_DEFAULT", "http://localhost:8000")}, headers=headers)
assert r2.status_code == 200, r2.text
run_id = r2.json()["run_id"]
r3 = client.get(f"/api/v1/runs/{run_id}", headers=headers)
assert r3.status_code == 200, r3.text
data = r3.json()
html = data.get("report_html") or data.get("signed_report_url")
print(html or "")
PY

# Print where the HTML report is
REPORT_PATH=$(ls -1 artifacts/run_*/report.html 2>/dev/null | tail -n 1 || true)
if [[ -n "$REPORT_PATH" ]]; then
  echo "HTML report: $APP_ROOT/$REPORT_PATH"
else
  echo "No report found yet. Check artifacts directory."
fi


