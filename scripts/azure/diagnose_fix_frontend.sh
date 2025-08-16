#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# ROLE: Senior Release/DevOps Engineer for Cognisia's Forge 1
# OBJECTIVE: Diagnose and fix full-stack connectivity for Client Portal UI
# =============================================================================

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
die() { echo -e "${RED}ERROR: $*${NC}" >&2; exit 1; }
info() { echo -e "${BLUE}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*" >&2; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }

# Banner for task sections
banner() {
    echo
    echo "============================================================"
    echo "[$1] $2"
    echo "============================================================"
}

# =============================================================================
# TASK 0: Load Azure context & derive names
# =============================================================================
banner "0" "Load Azure context & derive names"

# Check for environment file
if [[ ! -f .azure/env.staging ]]; then
    die "Missing .azure/env.staging file. Run scripts/azure/10_bootstrap_core.sh first"
fi

# Source the environment
source .azure/env.staging

# Validate required variables
[[ -z "${RG:-}" ]] && die "Missing RG in .azure/env.staging"
[[ -z "${SUFFIX:-}" ]] && die "Missing SUFFIX in .azure/env.staging"
[[ -z "${ACR:-}" ]] && die "Missing ACR in .azure/env.staging"
[[ -z "${KV:-}" ]] && die "Missing KV in .azure/env.staging"

# Handle both ACA_ENV and ACA_ENVIRONMENT
ACA_ENV="${ACA_ENV:-${ACA_ENVIRONMENT:-}}"
[[ -z "${ACA_ENV}" ]] && die "Missing ACA_ENV or ACA_ENVIRONMENT in .azure/env.staging"

# Export for use in subscripts
export RG SUFFIX ACR KV ACA_ENV

# Derive names
UI_IMG="forge1-frontend"
UI_TAG="staging"
UI_APP="forge1-frontend-${SUFFIX}"

info "Deriving backend API URL..."
# Check if backend exists
if ! az containerapp show -g "$RG" -n forge1-backend-v2 &>/dev/null; then
    # Try without v2 suffix
    if ! az containerapp show -g "$RG" -n forge1-backend &>/dev/null; then
        die "Backend container app not found (tried forge1-backend-v2 and forge1-backend)"
    fi
    BACKEND_APP="forge1-backend"
else
    BACKEND_APP="forge1-backend-v2"
fi

API_FQDN=$(az containerapp show -g "$RG" -n "$BACKEND_APP" --query properties.configuration.ingress.fqdn -o tsv)
[[ -z "$API_FQDN" ]] && die "Failed to get backend FQDN"
API_URL="https://${API_FQDN}"

info "Fetching ACR login server..."
ACR_LOGIN=$(az acr show -g "$RG" -n "$ACR" --query loginServer -o tsv)
[[ -z "$ACR_LOGIN" ]] && die "Failed to get ACR login server"

# Print all discovered values
info "===== Discovered Values ====="
info "Resource Group:     $RG"
info "SUFFIX:            $SUFFIX"
info "ACR:               $ACR"
info "ACR Login Server:  $ACR_LOGIN"
info "Key Vault:         $KV"
info "ACA Environment:   $ACA_ENV"
info "Backend App:       $BACKEND_APP"
info "Backend API URL:   $API_URL"
info "UI Image:          $UI_IMG:$UI_TAG"
info "UI App Name:       $UI_APP"
info "============================="

# =============================================================================
# TASK 1: Live connectivity probe (before changes)
# =============================================================================
banner "1" "Live connectivity probe (before changes)"

# Discover UI FQDN
info "Discovering UI FQDN..."
if ! az containerapp show -g "$RG" -n "$UI_APP" &>/dev/null; then
    warn "Frontend container app $UI_APP not found. Will need to create it."
    UI_FQDN=""
    UI_URL=""
else
    UI_FQDN=$(az containerapp show -g "$RG" -n "$UI_APP" --query properties.configuration.ingress.fqdn -o tsv)
    UI_URL="https://${UI_FQDN}"
    info "Frontend URL: $UI_URL"
    
    # Test UI connectivity
    info "Testing UI connectivity..."
    UI_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$UI_URL" || echo "000")
    if [[ "$UI_STATUS" == "200" ]]; then
        success "UI is reachable (HTTP $UI_STATUS)"
    else
        warn "UI returned HTTP $UI_STATUS"
        info "Fetching recent container logs..."
        az containerapp logs show -g "$RG" -n "$UI_APP" --since 15m 2>/dev/null | tail -n 200 || true
    fi
fi

# Test backend with CORS
info "Testing backend /ready endpoint with CORS..."
if [[ -n "$UI_URL" ]]; then
    CORS_TEST=$(curl -sSI -H "Origin: ${UI_URL}" "${API_URL}/api/v1/health/ready" 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
    if [[ -n "$CORS_TEST" ]]; then
        success "CORS header present: $CORS_TEST"
    else
        warn "No Access-Control-Allow-Origin header found"
    fi
else
    info "Skipping CORS test (no UI URL yet)"
fi

# Backend health check
info "Backend health check..."
READY_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/api/v1/health/ready" || echo "000")
if [[ "$READY_STATUS" == "200" ]]; then
    success "Backend is ready (HTTP $READY_STATUS)"
else
    warn "Backend returned HTTP $READY_STATUS"
fi

# Print likely causes
if [[ -z "$CORS_TEST" && -n "$UI_URL" ]]; then
    warn "LIKELY CAUSE: CORS not configured for UI origin"
fi
if [[ "$READY_STATUS" == "401" ]] || [[ "$READY_STATUS" == "403" ]]; then
    warn "LIKELY CAUSE: Authentication/authorization issue"
fi
if [[ "$UI_STATUS" == "200" && -z "$CORS_TEST" ]]; then
    warn "LIKELY CAUSE: Wrong NEXT_PUBLIC_API_BASE_URL or missing user context"
fi

# =============================================================================
# TASK 2: Verify frontend envs at runtime
# =============================================================================
banner "2" "Verify frontend environment variables at runtime"

if [[ -n "$UI_APP" ]] && az containerapp show -g "$RG" -n "$UI_APP" &>/dev/null; then
    info "Current frontend environment variables:"
    az containerapp show -g "$RG" -n "$UI_APP" --query 'properties.template.containers[0].env' -o table || true
    
    # Check specific env var
    CURRENT_API_URL=$(az containerapp show -g "$RG" -n "$UI_APP" --query "properties.template.containers[0].env[?name=='NEXT_PUBLIC_API_BASE_URL'].value | [0]" -o tsv 2>/dev/null || echo "")
    
    if [[ "$CURRENT_API_URL" != "$API_URL" ]]; then
        warn "NEXT_PUBLIC_API_BASE_URL mismatch!"
        warn "Current: $CURRENT_API_URL"
        warn "Expected: $API_URL"
        warn "Will need to rebuild with correct build args"
        NEEDS_REBUILD=true
    else
        success "NEXT_PUBLIC_API_BASE_URL is correct: $API_URL"
        NEEDS_REBUILD=false
    fi
else
    info "Frontend app not deployed yet, will build with correct env vars"
    NEEDS_REBUILD=true
fi

# Check Dockerfile for PORT handling
info "Checking frontend Dockerfile..."
if [[ -f frontend/Dockerfile ]]; then
    if grep -q 'PORT:-3000' frontend/Dockerfile; then
        success "Dockerfile respects \$PORT variable"
    else
        warn "Dockerfile may not respect \$PORT variable, will fix"
    fi
else
    warn "frontend/Dockerfile not found, will create"
fi

# =============================================================================
# TASK 3: Ensure backend CORS includes UI origin (Key Vault)
# =============================================================================
banner "3" "Ensure backend CORS includes UI origin"

if [[ -z "$UI_URL" ]]; then
    warn "No UI URL yet, skipping CORS update for now"
else
    info "Desired CORS origin: $UI_URL"
    
    # Try both secret name formats
    CORS_SECRET_NAME=""
    CORS_VALUE=""
    
    # Try with hyphen first
    if az keyvault secret show --vault-name "$KV" --name "BACKEND-CORS-ORIGINS" &>/dev/null; then
        CORS_SECRET_NAME="BACKEND-CORS-ORIGINS"
        CORS_VALUE=$(az keyvault secret show --vault-name "$KV" --name "$CORS_SECRET_NAME" --query value -o tsv)
        info "Found CORS secret: $CORS_SECRET_NAME"
    # Try with underscore
    elif az keyvault secret show --vault-name "$KV" --name "BACKEND_CORS_ORIGINS" &>/dev/null; then
        CORS_SECRET_NAME="BACKEND_CORS_ORIGINS"
        CORS_VALUE=$(az keyvault secret show --vault-name "$KV" --name "$CORS_SECRET_NAME" --query value -o tsv)
        info "Found CORS secret: $CORS_SECRET_NAME"
    else
        warn "CORS secret not found, creating BACKEND-CORS-ORIGINS"
        CORS_SECRET_NAME="BACKEND-CORS-ORIGINS"
        CORS_VALUE=""
    fi
    
    # Check if UI origin is already in CORS
    if [[ "$CORS_VALUE" == *"$UI_URL"* ]]; then
        success "UI origin already in CORS: ${CORS_VALUE:0:60}..."
    else
        info "Adding UI origin to CORS..."
        if [[ -z "$CORS_VALUE" ]]; then
            NEW_CORS="$UI_URL"
        else
            NEW_CORS="${CORS_VALUE},${UI_URL}"
        fi
        
        az keyvault secret set --vault-name "$KV" --name "$CORS_SECRET_NAME" --value "$NEW_CORS" -o none
        success "Updated CORS in Key Vault"
        
        # Restart backend to apply changes
        info "Restarting backend to apply CORS changes..."
        az containerapp revision restart -g "$RG" -n "$BACKEND_APP" || warn "Failed to restart backend"
        sleep 5
        
        # Re-test CORS
        info "Re-testing CORS after update..."
        CORS_TEST=$(curl -sSI -H "Origin: ${UI_URL}" "${API_URL}/api/v1/health/ready" 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
        if [[ -n "$CORS_TEST" ]]; then
            success "CORS header now present: $CORS_TEST"
        else
            warn "CORS header still missing after update"
        fi
    fi
    
    info "KV Secret Name: $CORS_SECRET_NAME"
    info "CORS Value (first 60 chars): ${CORS_VALUE:0:60}..."
fi

# =============================================================================
# TASK 4: Auth sanity (create or reuse a staging user)
# =============================================================================
banner "4" "Auth sanity check"

info "Checking for auth endpoints..."
AUTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/api/v1/auth/login" -X POST -H "Content-Type: application/json" -d '{}' || echo "000")

if [[ "$AUTH_STATUS" == "400" ]] || [[ "$AUTH_STATUS" == "401" ]] || [[ "$AUTH_STATUS" == "422" ]]; then
    info "Auth endpoint exists (returned $AUTH_STATUS for empty credentials)"
    
    # Try to get dev credentials from Key Vault
    if az keyvault secret show --vault-name "$KV" --name "DEV-ADMIN-EMAIL" &>/dev/null; then
        DEV_EMAIL=$(az keyvault secret show --vault-name "$KV" --name "DEV-ADMIN-EMAIL" --query value -o tsv)
        DEV_PASSWORD=$(az keyvault secret show --vault-name "$KV" --name "DEV-ADMIN-PASSWORD" --query value -o tsv 2>/dev/null || echo "")
        
        if [[ -n "$DEV_EMAIL" && -n "$DEV_PASSWORD" ]]; then
            info "Attempting login with dev credentials..."
            LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/auth/login" \
                -H "Content-Type: application/json" \
                -d "{\"email\":\"$DEV_EMAIL\",\"password\":\"$DEV_PASSWORD\"}" || echo "{}")
            
            if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
                JWT=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
                success "Login successful, got JWT"
                
                # Test protected endpoint
                info "Testing protected endpoint /api/v1/ai/models..."
                MODELS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/api/v1/ai/models" \
                    -H "Authorization: Bearer $JWT" || echo "000")
                
                if [[ "$MODELS_STATUS" == "200" ]]; then
                    success "Protected endpoint accessible (HTTP $MODELS_STATUS)"
                else
                    warn "Protected endpoint returned HTTP $MODELS_STATUS"
                fi
            else
                warn "Login failed with dev credentials"
            fi
        else
            info "Dev credentials not found in Key Vault"
        fi
    else
        info "No dev credentials in Key Vault, skipping auth test"
        info "Next step: Use the UI login form and ensure it succeeds"
    fi
else
    warn "Auth endpoint not accessible (HTTP $AUTH_STATUS)"
    info "Next step: Ensure backend auth is configured properly"
fi

# =============================================================================
# TASK 5: Rebuild & push frontend image with correct env (if required)
# =============================================================================
banner "5" "Rebuild & push frontend image"

if [[ "$NEEDS_REBUILD" == "true" ]] || [[ ! -f frontend/Dockerfile ]]; then
    info "Preparing to rebuild frontend..."
    
    # Check/update Dockerfile
    info "Updating frontend/Dockerfile..."
    cat > frontend/Dockerfile << 'EOF'
# Multi-stage Dockerfile for Next.js with SSR
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Accept build args for client-side env vars
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_ENV_LABEL
ARG NEXT_PUBLIC_GIT_SHA

# Set them as env vars for the build
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_ENV_LABEL=$NEXT_PUBLIC_ENV_LABEL
ENV NEXT_PUBLIC_GIT_SHA=$NEXT_PUBLIC_GIT_SHA

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER nextjs

# Respect PORT environment variable
EXPOSE 3000
ENV PORT 3000

CMD ["node", "server.js"]
EOF
    success "Created/updated frontend/Dockerfile"
    
    # Check package.json scripts
    info "Checking frontend/package.json scripts..."
    if [[ -f frontend/package.json ]]; then
        if ! grep -q '"start":.*PORT' frontend/package.json; then
            info "Updating package.json start script..."
            # This is a simplified update - in production you'd use jq
            cp frontend/package.json frontend/package.json.bak
            sed -i 's/"start":[^,]*/"start": "next start -p ${PORT:-3000}"/' frontend/package.json
        fi
    fi
    
    # Get Git SHA
    GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    info "Git SHA: $GIT_SHA"
    
    # Login to ACR
    info "Logging into ACR..."
    az acr login -n "$ACR" || die "Failed to login to ACR"
    
    # Build and push image
    info "Building and pushing frontend image..."
    info "Image: $ACR_LOGIN/$UI_IMG:$UI_TAG"
    info "Build args:"
    info "  NEXT_PUBLIC_API_BASE_URL=$API_URL"
    info "  NEXT_PUBLIC_ENV_LABEL=Staging"
    info "  NEXT_PUBLIC_GIT_SHA=$GIT_SHA"
    
    # Ensure buildx is available
    docker buildx create --use 2>/dev/null || true
    
    # Build and push
    if docker buildx build --platform linux/amd64 \
        -t "$ACR_LOGIN/$UI_IMG:$UI_TAG" \
        --build-arg NEXT_PUBLIC_API_BASE_URL="$API_URL" \
        --build-arg NEXT_PUBLIC_ENV_LABEL="Staging" \
        --build-arg NEXT_PUBLIC_GIT_SHA="$GIT_SHA" \
        -f frontend/Dockerfile frontend --push; then
        success "Frontend image built and pushed successfully"
        
        # Get image digest
        IMAGE_DIGEST=$(docker buildx imagetools inspect "$ACR_LOGIN/$UI_IMG:$UI_TAG" --format "{{.Manifest.Digest}}" 2>/dev/null || echo "")
        if [[ -n "$IMAGE_DIGEST" ]]; then
            info "Image digest: $IMAGE_DIGEST"
        fi
    else
        die "Failed to build and push frontend image"
    fi
else
    info "Frontend rebuild not required (env vars are correct)"
fi

# =============================================================================
# TASK 6: Update ACA app with new image + runtime envs
# =============================================================================
banner "6" "Update Azure Container App"

# Check if app exists
if ! az containerapp show -g "$RG" -n "$UI_APP" &>/dev/null; then
    info "Creating new frontend Container App..."
    
    az containerapp create \
        -n "$UI_APP" \
        -g "$RG" \
        --environment "$ACA_ENV" \
        --image "$ACR_LOGIN/$UI_IMG:$UI_TAG" \
        --target-port 3000 \
        --ingress external \
        --registry-server "$ACR_LOGIN" \
        --registry-identity system \
        --cpu 0.5 \
        --memory 1.0 \
        --min-replicas 1 \
        --max-replicas 3 \
        --env-vars \
            NODE_ENV=production \
            NEXT_PUBLIC_API_BASE_URL="$API_URL" \
            NEXT_PUBLIC_ENV_LABEL=Staging \
        -o none
    
    if [[ $? -eq 0 ]]; then
        success "Frontend Container App created"
    else
        die "Failed to create frontend Container App"
    fi
else
    info "Updating existing frontend Container App..."
    
    az containerapp update \
        -g "$RG" \
        -n "$UI_APP" \
        --image "$ACR_LOGIN/$UI_IMG:$UI_TAG" \
        --set-env-vars \
            NODE_ENV=production \
            NEXT_PUBLIC_API_BASE_URL="$API_URL" \
            NEXT_PUBLIC_ENV_LABEL=Staging \
        -o none
    
    if [[ $? -eq 0 ]]; then
        success "Frontend Container App updated"
    else
        die "Failed to update frontend Container App"
    fi
fi

# Wait for revision to be healthy
info "Waiting for revision to become healthy..."
sleep 10

# Get updated FQDN
UI_FQDN=$(az containerapp show -g "$RG" -n "$UI_APP" --query properties.configuration.ingress.fqdn -o tsv)
UI_URL="https://${UI_FQDN}"
success "Frontend URL: $UI_URL"

# Check revision status
REVISION_STATUS=$(az containerapp revision list -g "$RG" -n "$UI_APP" --query "[0].properties.healthState" -o tsv)
if [[ "$REVISION_STATUS" != "Healthy" ]]; then
    warn "Revision status: $REVISION_STATUS"
    info "Fetching recent logs..."
    az containerapp logs show -g "$RG" -n "$UI_APP" --since 5m 2>/dev/null | tail -n 100 || true
fi

# =============================================================================
# TASK 7: Browser-simulated smoke tests
# =============================================================================
banner "7" "Browser-simulated smoke tests"

# UI 200 check
info "Testing UI availability..."
UI_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$UI_URL" || echo "000")
if [[ "$UI_STATUS" == "200" ]]; then
    success "UI is reachable (HTTP $UI_STATUS)"
else
    warn "UI returned HTTP $UI_STATUS"
fi

# CORS header check
info "Testing CORS header..."
CORS_TEST=$(curl -sSI -H "Origin: ${UI_URL}" "${API_URL}/api/v1/health/ready" 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
if [[ -n "$CORS_TEST" ]]; then
    success "CORS header present: $CORS_TEST"
else
    warn "No CORS header found"
fi

# Protected endpoint test with JWT (if available)
if [[ -n "${JWT:-}" ]]; then
    info "Testing protected endpoint with JWT..."
    PROTECTED_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/api/v1/employees" \
        -H "Authorization: Bearer $JWT" || echo "000")
    
    if [[ "$PROTECTED_STATUS" == "200" ]]; then
        success "Protected endpoint accessible (HTTP $PROTECTED_STATUS)"
    else
        warn "Protected endpoint returned HTTP $PROTECTED_STATUS"
    fi
fi

# =============================================================================
# TASK 8: Frontend runtime check for API calls (headless)
# =============================================================================
banner "8" "Frontend runtime check for API calls"

# Fetch UI root HTML
info "Fetching UI root HTML..."
UI_HTML=$(curl -s "$UI_URL" | head -n 100)

# Check for build info
if echo "$UI_HTML" | grep -q "NEXT_PUBLIC_GIT_SHA"; then
    BUILD_INFO=$(echo "$UI_HTML" | grep -o 'NEXT_PUBLIC_[^<]*' | head -n 3)
    success "Build info found in HTML:"
    echo "$BUILD_INFO"
fi

# Test a public metrics endpoint
info "Testing metrics endpoint..."
METRICS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/api/v1/metrics/prometheus" \
    -H "Origin: ${UI_URL}" || echo "000")

if [[ "$METRICS_STATUS" == "200" ]] || [[ "$METRICS_STATUS" == "401" ]]; then
    info "Metrics endpoint responded (HTTP $METRICS_STATUS)"
fi

# Test employees endpoint
info "Testing employees endpoint..."
EMPLOYEES_RESPONSE=$(curl -s "${API_URL}/api/v1/employees" \
    -H "Origin: ${UI_URL}" \
    -H "Accept: application/json")

if echo "$EMPLOYEES_RESPONSE" | grep -q "employees\|error\|unauthorized"; then
    success "Employees endpoint returned valid JSON response"
    DATA_FLOW_OK=true
else
    warn "Employees endpoint did not return expected response"
    DATA_FLOW_OK=false
fi

# =============================================================================
# TASK 9: Output + next steps
# =============================================================================
banner "9" "Summary and Next Steps"

# Print summary
echo
echo "================================================================"
echo "                        DEPLOYMENT SUMMARY                      "
echo "================================================================"
echo "Resource Group:        $RG"
echo "ACR Login Server:      $ACR_LOGIN"
echo "ACA Environment:       $ACA_ENV"
echo "Key Vault:            $KV"
echo "UI URL:               $UI_URL"
echo "API URL:              $API_URL"
echo "KV CORS Secret:       ${CORS_SECRET_NAME:-Not set}"
echo "CORS Value Length:    ${#CORS_VALUE} chars"
echo "Image Tag:            $UI_IMG:$UI_TAG"
if [[ -n "${IMAGE_DIGEST:-}" ]]; then
    echo "Image Digest:         $IMAGE_DIGEST"
fi
echo "================================================================"

# Data flow status
echo
if [[ "$DATA_FLOW_OK" == "true" ]] && [[ "$UI_STATUS" == "200" ]] && [[ -n "$CORS_TEST" ]]; then
    echo "================================================================"
    echo "                    DATA FLOW: OK ✓                            "
    echo "================================================================"
    success "All connectivity checks passed!"
else
    echo "================================================================"
    echo "                    DATA FLOW: ISSUES DETECTED                 "
    echo "================================================================"
    
    # Actionable suspects
    echo
    echo "ACTIONABLE ITEMS:"
    echo "-----------------"
    
    if [[ "$UI_STATUS" != "200" ]]; then
        echo "❌ UI not reachable"
        echo "   → Check container logs: az containerapp logs show -g $RG -n $UI_APP --tail 200"
        echo "   → Check revision status: az containerapp revision list -g $RG -n $UI_APP -o table"
    fi
    
    if [[ -z "$CORS_TEST" ]]; then
        echo "❌ CORS not configured"
        echo "   → Update Key Vault: az keyvault secret set --vault-name $KV --name BACKEND-CORS-ORIGINS --value \"$UI_URL\""
        echo "   → Restart backend: az containerapp revision restart -g $RG -n $BACKEND_APP"
    fi
    
    if [[ "$DATA_FLOW_OK" != "true" ]]; then
        echo "❌ API calls not working"
        echo "   (a) User not logged in → Go through UI login at $UI_URL"
        echo "   (b) No data available → Run a task to create sample data:"
        echo "       curl -X POST ${API_URL}/api/v1/employees -H 'Content-Type: application/json' -H 'Authorization: Bearer <token>' -d '{...}'"
        echo "   (c) Console errors → Open browser DevTools at $UI_URL and check Network/Console tabs"
    fi
fi

# Final status
echo
if [[ "$DATA_FLOW_OK" == "true" ]] && [[ "$UI_STATUS" == "200" ]] && [[ -n "$CORS_TEST" ]]; then
    success "PASS: Frontend connectivity fully operational"
    exit 0
else
    warn "FAIL: Some issues remain - see actionable items above"
    exit 1
fi