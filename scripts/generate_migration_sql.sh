#!/usr/bin/env bash
set -euo pipefail

# Generate offline migration SQL for Alembic
# This script generates SQL that can be applied directly to the database
# without running Alembic in the production environment

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"
OUTPUT_FILE="${1:-$SCRIPT_DIR/../deploy.sql}"

echo "Generating offline migration SQL..."

cd "$BACKEND_DIR"

# Use Docker to generate SQL in a clean environment
docker run --rm -v "$PWD":/app -w /app python:3.11-slim sh -c '
  pip install -q --no-cache-dir alembic sqlalchemy psycopg pgvector psycopg-binary && \
  python -c "
import os
os.environ[\"DATABASE_URL\"] = \"postgresql://dummy:dummy@dummy:5432/dummy\"
" && \
  alembic -c alembic.ini upgrade head --sql
' > "$OUTPUT_FILE.tmp" 2>/dev/null

# Clean up the output to remove non-SQL content
grep -E "^(CREATE|ALTER|DROP|INSERT|UPDATE|DELETE|BEGIN|COMMIT|SET|--)" "$OUTPUT_FILE.tmp" > "$OUTPUT_FILE" || true
rm -f "$OUTPUT_FILE.tmp"

if [ -s "$OUTPUT_FILE" ]; then
  echo "Migration SQL generated successfully at: $OUTPUT_FILE"
  echo "Preview:"
  head -20 "$OUTPUT_FILE"
  echo "..."
  echo "Total lines: $(wc -l < "$OUTPUT_FILE")"
else
  echo "Warning: No migration SQL generated or file is empty"
  echo "-- No migrations needed" > "$OUTPUT_FILE"
fi
