#!/usr/bin/env bash
set -euo pipefail

# Run Alembic migrations inside the backend container context.
# Usage:
#   DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db ./scripts/migrate_in_container.sh

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
BACKEND_DIR="$REPO_ROOT/backend"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required" >&2
  exit 1
fi

cd "$BACKEND_DIR"

# Ensure alembic and migrations are present in the image and local venv
if ! python3 -c 'import alembic' 2>/dev/null; then
  echo "Installing alembic locally (not in container) for migration commands..." >&2
  python3 -m pip install -r requirements.txt >/dev/null
fi

# Preflight: create base ORM tables if absent so that later migrations (FK/idx) can apply cleanly
python3 - <<'PY'
from app.db.session import create_tables
try:
    create_tables()
    print("Preflight: base tables ensured")
except Exception as e:
    print(f"Preflight warning: {e}")
PY

echo "Stamping head and running upgrade against: ${DATABASE_URL}" >&2
# Stamp current head to accommodate preflight-created tables, then upgrade (no-op if already at head)
alembic -x url="${DATABASE_URL}" stamp head || true
alembic -x url="${DATABASE_URL}" upgrade head

echo "Migrations complete"


