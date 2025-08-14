#!/usr/bin/env bash
set -euo pipefail

PORT=${PORT:-54329}
DB=${DB:-forge1}
PGUSER_ENV=${PGUSER:-}
USER=${PGUSER_ENV:-postgres}
PASSWORD=${PASSWORD:-test}

docker rm -f forge1-pg >/dev/null 2>&1 || true
# Use pgvector-enabled image for local testing
docker run -d --name forge1-pg -e POSTGRES_PASSWORD="$PASSWORD" -e POSTGRES_DB="$DB" -p "$PORT":5432 pgvector/pgvector:pg14 >/dev/null

echo "Waiting for postgres to become available on port ${PORT}..." >&2
until docker exec forge1-pg pg_isready -U "$USER" >/dev/null 2>&1; do sleep 1; done

echo "Creating pgvector extension..." >&2
docker exec -u postgres forge1-pg psql -U postgres -d "$DB" -c 'CREATE EXTENSION IF NOT EXISTS vector;' >/dev/null

export DATABASE_URL="postgresql+psycopg://${USER}:${PASSWORD}@localhost:${PORT}/${DB}"
echo "DATABASE_URL=${DATABASE_URL}"
echo "Postgres ready. Run migrations with: DATABASE_URL=... ./scripts/migrate_in_container.sh" >&2


