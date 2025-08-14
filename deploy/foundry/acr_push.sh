#!/usr/bin/env bash
set -euo pipefail

# Usage: ./acr_push.sh <acr_name> <image_name> [tag]
# Example: ./acr_push.sh myacr forge1-backend v1

ACR_NAME=${1:-}
IMAGE_NAME=${2:-forge1-backend}
TAG=${3:-latest}

if [[ -z "$ACR_NAME" ]]; then
  echo "Usage: $0 <acr_name> <image_name> [tag]" >&2
  exit 1
fi

REGISTRY="${ACR_NAME}.azurecr.io"
IMAGE="${REGISTRY}/${IMAGE_NAME}:${TAG}"

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/../.." &> /dev/null && pwd)

echo "Logging in to ACR ${REGISTRY}"
az acr login --name "${ACR_NAME}"

echo "Building image ${IMAGE}"
docker build -t "${IMAGE}" -f "${REPO_ROOT}/backend/Dockerfile" "${REPO_ROOT}/backend"

echo "Pushing ${IMAGE}"
docker push "${IMAGE}"

echo "Done"


