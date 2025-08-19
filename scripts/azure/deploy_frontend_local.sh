#!/usr/bin/env bash
set -euo pipefail

# Local build and test script for Forge 1 Frontend
# This script builds the Docker image locally for testing

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*" >&2; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
die() { error "$*"; exit 1; }

# Load environment
load_env() {
    info "Loading environment configuration..."
    
    ENV_FILE="$PROJECT_ROOT/.azure/env.staging"
    if [[ -f "$ENV_FILE" ]]; then
        source "$ENV_FILE"
    fi
    
    # Set defaults for local testing
    BACKEND_URL="${BACKEND_URL:-https://forge1-backend-v2.agreeablebush-fb7c993c.eastus.azurecontainerapps.io}"
    GIT_SHA=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo "local")
    
    info "Configuration:"
    info "  Backend URL: $BACKEND_URL"
    info "  Git SHA: $GIT_SHA"
}

# Build Docker image locally
build_local() {
    info "Building Docker image locally..."
    
    cd "$PROJECT_ROOT/frontend"
    
    IMAGE_NAME="forge1-frontend:local"
    
    info "Building image: $IMAGE_NAME"
    
    docker build \
        --build-arg "NEXT_PUBLIC_API_BASE_URL=${BACKEND_URL}" \
        --build-arg "NEXT_PUBLIC_ENV_LABEL=Local" \
        --build-arg "NEXT_PUBLIC_GIT_SHA=${GIT_SHA}" \
        --tag "$IMAGE_NAME" \
        . || die "Docker build failed"
    
    info "Image built successfully: $IMAGE_NAME"
}

# Run container locally
run_local() {
    info "Running container locally..."
    
    CONTAINER_NAME="forge1-frontend-local"
    
    # Stop existing container if running
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        info "Stopping existing container..."
        docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
        docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
    
    info "Starting container on port 3000..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        -p 3000:3000 \
        -e NODE_ENV=production \
        -e NEXT_PUBLIC_API_BASE_URL="$BACKEND_URL" \
        -e NEXT_PUBLIC_ENV_LABEL="Local" \
        -e NEXT_PUBLIC_GIT_SHA="$GIT_SHA" \
        forge1-frontend:local || die "Failed to start container"
    
    info "Container started: $CONTAINER_NAME"
    info "Waiting for app to be ready..."
    sleep 5
}

# Test local deployment
test_local() {
    info "Testing local deployment..."
    
    LOCAL_URL="http://localhost:3000"
    
    info "Testing frontend URL: $LOCAL_URL"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$LOCAL_URL" || echo "000")
    
    if [[ "$HTTP_CODE" == "200" ]]; then
        info "✓ Frontend is responding (HTTP $HTTP_CODE)"
    else
        warn "Frontend returned HTTP $HTTP_CODE (expected 200)"
    fi
    
    # Show container logs
    info "Container logs (last 20 lines):"
    docker logs --tail 20 forge1-frontend-local
}

# Print summary
print_summary() {
    echo
    info "========================================="
    info "Local Build Summary"
    info "========================================="
    info "Image:        forge1-frontend:local"
    info "Container:    forge1-frontend-local"
    info "Local URL:    http://localhost:3000"
    info "Backend URL:  $BACKEND_URL"
    info "========================================="
    echo
    info "🚀 Local build complete!"
    info "Visit: http://localhost:3000"
    echo
    info "To stop the container: docker stop forge1-frontend-local"
    info "To view logs: docker logs forge1-frontend-local"
}

# Main execution
main() {
    info "Starting Forge 1 Frontend local build..."
    
    command -v docker >/dev/null 2>&1 || die "Docker not found. Please install Docker"
    
    load_env
    build_local
    run_local
    test_local
    print_summary
}

# Run main function
main "$@"
