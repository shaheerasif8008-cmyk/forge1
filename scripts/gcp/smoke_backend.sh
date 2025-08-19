#!/usr/bin/env bash
set -euo pipefail

URL="$1"
if [[ -z "${URL:-}" ]]; then
  echo "Usage: $0 https://<cloud-run-url>" >&2
  exit 1
fi
echo "Smoke: $URL"
curl -fsS "$URL/api/v1/health/live" | grep -q '"status":"live"'
code=$(curl -s -o /dev/null -w "%{http_code}" "$URL/api/v1/health/ready")
test "$code" = "200"
echo OK


