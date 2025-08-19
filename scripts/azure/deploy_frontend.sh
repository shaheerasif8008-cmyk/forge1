#!/usr/bin/env bash
set -euo pipefail

# Deploy Forge 1 Frontend to Azure Container Apps
# This script handles the complete deployment process for the Next.js SSR frontend

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

# Check prerequisites
check_prereqs() {
    info "Checking prerequisites..."
    command -v az >/dev/null 2>&1 || die "Azure CLI not found. Please install: https://aka.ms/InstallAzureCLIDeb"
    command -v docker >/dev/null 2>&1 || die "Docker not found. Please install Docker"
    command -v git >/dev/null 2>&1 || die "Git not found"
    
    # Check Azure login
    az account show >/dev/null 2>&1 || die "Not logged in to Azure. Run: az login"
    
    info "Prerequisites check passed"
}

# Load environment variables
load_env() {
    info "Loading environment configuration..."
    
    ENV_FILE="$PROJECT_ROOT/.azure/env.staging"
    if [[ ! -f "$ENV_FILE" ]]; then
        die "Environment file not found: $ENV_FILE"
    fi
    
    source "$ENV_FILE"
    
    # Validate required variables
    [[ -n "${RG:-}" ]] || die "RG not set in env file"
    [[ -n "${SUFFIX:-}" ]] || die "SUFFIX not set in env file"
    [[ -n "${ACR:-}" ]] || die "ACR not set in env file"
    [[ -n "${KV:-}" ]] || die "KV not set in env file"
    [[ -n "${ACA_ENV:-${ACA_ENVIRONMENT:-}}" ]] || die "ACA_ENV/ACA_ENVIRONMENT not set in env file"
    
    # Use ACA_ENV or fallback to ACA_ENVIRONMENT
    ACA_ENV="${ACA_ENV:-$ACA_ENVIRONMENT}"
    
    # Derive frontend-specific variables
    UI_IMG="forge1-frontend"
    UI_TAG="staging"
    UI_APP="forge1-frontend-${SUFFIX}"
    
    # Get ACR login server
    ACR_LOGIN=$(az acr show -g "$RG" -n "$ACR" --query loginServer -o tsv 2>/dev/null) || {
        warn "Could not fetch ACR login server. Using constructed value."
        ACR_LOGIN="${ACR}.azurecr.io"
    }
    
    # Get Git SHA for versioning
    GIT_SHA=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown")
    
    # Backend URL
    BACKEND_URL="${BACKEND_URL:-https://forge1-backend-v2.agreeablebush-fb7c993c.eastus.azurecontainerapps.io}"
    
    info "Environment loaded:"
    info "  Resource Group: $RG"
    info "  ACR: $ACR_LOGIN"
    info "  Container App: $UI_APP"
    info "  Backend URL: $BACKEND_URL"
    info "  Git SHA: $GIT_SHA"
}

# Build and push Docker image
build_and_push() {
    info "Building and pushing Docker image..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # Login to ACR
    info "Logging in to ACR..."
    az acr login --name "$ACR" || die "Failed to login to ACR"
    
    # Full image name
    FULL_IMAGE="${ACR_LOGIN}/${UI_IMG}:${UI_TAG}"
    
    info "Building image: $FULL_IMAGE"
    
    # Check if we need to use buildx for cross-platform
    if [[ "$(uname -m)" == "arm64" ]] || [[ "$(uname -m)" == "aarch64" ]]; then
        info "Detected ARM architecture, using buildx for linux/amd64"
        
        # Ensure buildx is available
        docker buildx create --use --name forge1-builder 2>/dev/null || true
        
        docker buildx build \
            --platform linux/amd64 \
            --build-arg "NEXT_PUBLIC_API_BASE_URL=${BACKEND_URL}" \
            --build-arg "NEXT_PUBLIC_ENV_LABEL=Staging" \
            --build-arg "NEXT_PUBLIC_GIT_SHA=${GIT_SHA}" \
            --tag "$FULL_IMAGE" \
            --push \
            . || die "Docker build failed"
    else
        # Standard build for x86_64
        docker build \
            --build-arg "NEXT_PUBLIC_API_BASE_URL=${BACKEND_URL}" \
            --build-arg "NEXT_PUBLIC_ENV_LABEL=Staging" \
            --build-arg "NEXT_PUBLIC_GIT_SHA=${GIT_SHA}" \
            --tag "$FULL_IMAGE" \
            . || die "Docker build failed"
        
        info "Pushing image to ACR..."
        docker push "$FULL_IMAGE" || die "Docker push failed"
    fi
    
    info "Image successfully pushed: $FULL_IMAGE"
}

# Create or update Container App
deploy_container_app() {
    info "Deploying to Azure Container Apps..."
    
    # Check if app exists
    if az containerapp show -g "$RG" -n "$UI_APP" >/dev/null 2>&1; then
        info "Container App exists, updating..."
        
        # Update the container app
        az containerapp update \
            -g "$RG" \
            -n "$UI_APP" \
            --image "${ACR_LOGIN}/${UI_IMG}:${UI_TAG}" \
            --set-env-vars \
                "NODE_ENV=production" \
                "NEXT_PUBLIC_ENV_LABEL=Staging" \
                "NEXT_PUBLIC_API_BASE_URL=${BACKEND_URL}" \
                "NEXT_PUBLIC_GIT_SHA=${GIT_SHA}" \
            --output none || die "Failed to update Container App"
    else
        info "Creating new Container App..."
        
        # Create the container app
        az containerapp create \
            -g "$RG" \
            -n "$UI_APP" \
            --environment "$ACA_ENV" \
            --image "${ACR_LOGIN}/${UI_IMG}:${UI_TAG}" \
            --target-port 3000 \
            --ingress external \
            --registry-server "$ACR_LOGIN" \
            --cpu 0.5 \
            --memory 1.0Gi \
            --min-replicas 1 \
            --max-replicas 3 \
            --env-vars \
                "NODE_ENV=production" \
                "NEXT_PUBLIC_ENV_LABEL=Staging" \
                "NEXT_PUBLIC_API_BASE_URL=${BACKEND_URL}" \
                "NEXT_PUBLIC_GIT_SHA=${GIT_SHA}" \
            --output none || die "Failed to create Container App"
    fi
    
    # Get the FQDN
    UI_FQDN=$(az containerapp show -g "$RG" -n "$UI_APP" --query properties.configuration.ingress.fqdn -o tsv)
    UI_URL="https://${UI_FQDN}"
    
    info "Container App deployed: $UI_URL"
}

# Update CORS in Key Vault
update_cors() {
    info "Updating backend CORS configuration..."
    
    # Try different secret names
    SECRET_NAME=""
    for name in "BACKEND-CORS-ORIGINS" "BACKEND_CORS_ORIGINS"; do
        if az keyvault secret show --vault-name "$KV" --name "$name" >/dev/null 2>&1; then
            SECRET_NAME="$name"
            break
        fi
    done
    
    if [[ -z "$SECRET_NAME" ]]; then
        warn "CORS secret not found in Key Vault, creating new one..."
        SECRET_NAME="BACKEND-CORS-ORIGINS"
        az keyvault secret set \
            --vault-name "$KV" \
            --name "$SECRET_NAME" \
            --value "$UI_URL" \
            --output none || warn "Failed to create CORS secret"
    else
        # Get current CORS origins
        CURRENT_CORS=$(az keyvault secret show --vault-name "$KV" --name "$SECRET_NAME" --query value -o tsv)
        
        # Check if UI URL is already in CORS
        if [[ "$CURRENT_CORS" == *"$UI_URL"* ]]; then
            info "UI URL already in CORS origins"
        else
            # Append UI URL to CORS
            if [[ -n "$CURRENT_CORS" ]]; then
                NEW_CORS="${CURRENT_CORS},${UI_URL}"
            else
                NEW_CORS="$UI_URL"
            fi
            
            info "Adding UI URL to CORS origins..."
            az keyvault secret set \
                --vault-name "$KV" \
                --name "$SECRET_NAME" \
                --value "$NEW_CORS" \
                --output none || warn "Failed to update CORS secret"
        fi
    fi
    
    # Restart backend to apply CORS changes
    info "Restarting backend to apply CORS changes..."
    BACKEND_APP="forge1-backend-v2"
    if az containerapp show -g "$RG" -n "$BACKEND_APP" >/dev/null 2>&1; then
        az containerapp revision restart \
            -g "$RG" \
            -n "$BACKEND_APP" \
            --revision $(az containerapp show -g "$RG" -n "$BACKEND_APP" --query properties.latestRevisionName -o tsv) \
            --output none || warn "Failed to restart backend"
        info "Backend restarted"
    else
        warn "Backend app not found, skipping restart"
    fi
}

# Perform smoke tests
smoke_test() {
    info "Performing smoke tests..."
    
    # Wait a bit for the app to be ready
    info "Waiting for app to be ready..."
    sleep 10
    
    # Test frontend health
    info "Testing frontend URL: $UI_URL"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$UI_URL" || echo "000")
    
    if [[ "$HTTP_CODE" == "200" ]]; then
        info "✓ Frontend is responding (HTTP $HTTP_CODE)"
    else
        warn "Frontend returned HTTP $HTTP_CODE (expected 200)"
    fi
    
    # Test backend CORS
    info "Testing backend CORS..."
    BACKEND_HEALTH="${BACKEND_URL}/health"
    CORS_HEADER=$(curl -s -I -H "Origin: $UI_URL" "$BACKEND_HEALTH" 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
    
    if [[ -n "$CORS_HEADER" ]]; then
        info "✓ Backend CORS header present: $CORS_HEADER"
    else
        warn "Backend CORS header not found or backend not responding"
    fi
}

# Print summary
print_summary() {
    echo
    info "========================================="
    info "Deployment Summary"
    info "========================================="
    info "Resource Group:    $RG"
    info "ACR:              $ACR_LOGIN"
    info "Container App:    $UI_APP"
    info "Image:            ${ACR_LOGIN}/${UI_IMG}:${UI_TAG}"
    info "Frontend URL:     $UI_URL"
    info "Backend URL:      $BACKEND_URL"
    info "Git SHA:          $GIT_SHA"
    info "========================================="
    echo
    info "🚀 Frontend deployment complete!"
    info "Visit: $UI_URL"
}

# Main execution
main() {
    info "Starting Forge 1 Frontend deployment..."
    
    check_prereqs
    load_env
    build_and_push
    deploy_container_app
    update_cors
    smoke_test
    print_summary
}

# Run main function
main "$@"
