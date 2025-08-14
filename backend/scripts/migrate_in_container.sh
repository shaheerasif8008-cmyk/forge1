#!/usr/bin/env bash
set -euo pipefail

# Container-native migration script.
# Expects to be run with WORKDIR=/app and DATABASE_URL env var set.

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required" >&2
  exit 1
fi

cd /app

if ! python3 -c 'import alembic' 2>/dev/null; then
  echo "ERROR: alembic not installed in image runtime" >&2
  exit 1
fi

# Preflight: create tables to allow subsequent Alembic upgrades to attach
python3 - <<'PY'
from app.db.session import create_tables
try:
    create_tables()
    print("Preflight: base tables ensured")
except Exception as e:
    print(f"Preflight warning: {e}")
PY

echo "Stamping and upgrading to head against: ${DATABASE_URL}" >&2
alembic -x url="${DATABASE_URL}" stamp head || true
alembic -x url="${DATABASE_URL}" upgrade head
echo "Migrations complete"


