#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Azure Ops Pack - Build & Push Backend Image to ACR (staging)

Reads .azure/env.staging to resolve ACR. Builds image and pushes to ACR.

Options:
  --context <dir>   Build context (default: repo root)
  --tag <tag>       Image tag (default: staging)

Usage:
  bash scripts/azure/30_build_push_backend.sh [--context .] [--tag staging]
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=./lib_common.sh
source "$SCRIPT_DIR/lib_common.sh"

read_env
ensure_logged_in

CONTEXT="${PWD}"
TAG="staging"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --context) CONTEXT="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    *) die "Unknown arg: $1" ;;
  esac
done

ACR_LOGIN=$(az acr show -n "$ACR" --query loginServer -o tsv)
IMAGE="$ACR_LOGIN/forge1-backend:${TAG}"

info "Logging in to ACR: $ACR"
az acr login -n "$ACR" >/dev/null

DOCKERFILE_PATH="${CONTEXT}/forge1-backend/Dockerfile"
BUILD_DIR="${CONTEXT}/forge1-backend"
if [[ ! -f "$DOCKERFILE_PATH" ]]; then
  DOCKERFILE_PATH="${CONTEXT}/backend/Dockerfile"
  BUILD_DIR="${CONTEXT}/backend"
fi
[[ -f "$DOCKERFILE_PATH" ]] || die "Dockerfile not found (checked forge1-backend/Dockerfile and backend/Dockerfile)"

info "Building image (linux/amd64): $IMAGE using $DOCKERFILE_PATH"
docker buildx build --platform linux/amd64 -f "$DOCKERFILE_PATH" -t "$IMAGE" --push "$BUILD_DIR"

echo "$IMAGE"

exit 0

#!/usr/bin/env bash
set -euo pipefail

# Build and push backend image to ACR
# Usage: bash scripts/azure/30_build_push_backend.sh [--context <path>] [--tag <tag>]

if [[ ! -f .azure/env.staging ]]; then
  echo ".azure/env.staging not found. Run 10_bootstrap_core.sh first." >&2
  exit 1
fi
source .azure/env.staging

CONTEXT="${1:-}"
TAG="staging"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --context)
      CONTEXT="$2"; shift 2;;
    --tag)
      TAG="$2"; shift 2;;
    *) echo "Unknown arg: $1" >&2; exit 1;;
  esac
done

if [[ -z "$CONTEXT" ]]; then CONTEXT="."; fi

LOGIN_SERVER=$(az acr show -n "$ACR" --query loginServer -o tsv)
IMAGE="$LOGIN_SERVER/forge1-backend:$TAG"

echo "Logging into ACR $ACR"
az acr login -n "$ACR" >/dev/null

echo "Building image $IMAGE from $CONTEXT/backend"
docker build -t "$IMAGE" -f "$CONTEXT/backend/Dockerfile" "$CONTEXT/backend"

echo "Pushing $IMAGE"
docker push "$IMAGE"
echo "Pushed $IMAGE"


