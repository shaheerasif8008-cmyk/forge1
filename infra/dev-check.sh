#!/usr/bin/env bash
set -euo pipefail

echo "Checking prerequisites..."

command -v docker >/dev/null 2>&1 || { echo "Docker is not installed"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "Docker Compose v2 is not available"; exit 1; }
command -v python >/dev/null 2>&1 || { echo "Python is not installed"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm is not installed"; exit 1; }

echo "Docker version: $(docker --version)"
echo "Python version: $(python --version)"
echo "npm version: $(npm --version)"

echo "Verifying .env file..."
if [ ! -f .env ]; then
  echo ".env not found at repo root. Copying from .env.example"
  cp .env.example .env
fi

echo "Running docker-compose config..."
docker compose config >/dev/null

echo "All checks passed."


