#!/usr/bin/env bash
set -euo pipefail

export DATABASE_URL="postgresql+psycopg://forge:forge@127.0.0.1:5542/forge1_local"

cd "$(dirname "$0")/.." 

echo "Using DATABASE_URL=${DATABASE_URL}"

cd backend

alembic upgrade head
echo
alembic current

#!/usr/bin/env bash
set -euo pipefail

# Idempotent local migration helper for Forge1
# Usage: scripts/migrate_local.sh

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://forge:forge@127.0.0.1:5542/forge1_local}"

echo "[migrate_local] Using DATABASE_URL=${DATABASE_URL}"

cd "$ROOT_DIR/backend"

# Create venv if missing
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

# Install alembic if missing
python3 - <<'PY'
import importlib, sys
try:
    importlib.import_module('alembic')
except ImportError:
    sys.exit(1)
PY
if [ $? -ne 0 ]; then
  python3 -m pip install -r requirements.txt
fi

echo "[migrate_local] Upgrading to head..."
alembic upgrade head

echo "[migrate_local] Current revision:"
alembic current -v || true

echo "[migrate_local] Done."


