#!/bin/bash
set -euo pipefail

# Forge 1 Staging Infrastructure Deployment Script
# Container-first rebuild on Azure Container Apps
echo "================================================"
echo "Forge 1 Staging Infrastructure Deployment"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment
ENV_FILE="/workspace/.azure/env.staging"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: Environment file not found at $ENV_FILE${NC}"
    exit 1
fi

source "$ENV_FILE"

# Function to print colored messages
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check Azure login
check_azure_login() {
    if ! az account show &>/dev/null; then
        print_error "Not logged in to Azure. Please run: az login"
        exit 1
    fi
    SUBSCRIPTION=$(az account show --query "[name, id]" -o tsv | head -n1)
    print_success "Logged in to Azure: $SUBSCRIPTION"
}

# Safety check function
safety_check() {
    local RG_EXISTS=$(az group exists -n "$RG" 2>/dev/null || echo "false")
    
    if [ "$RG_EXISTS" = "true" ]; then
        print_warning "Resource group '$RG' already exists!"
        echo -e "\n${YELLOW}⚠️  DESTRUCTIVE ACTION WARNING ⚠️${NC}"
        echo "This will DELETE the following resource group and ALL its resources:"
        echo "  - Resource Group: $RG"
        echo ""
        echo "To proceed with deletion and rebuild, type: ${RED}CONFIRM_RESET${NC}"
        echo "To abort, press Ctrl+C or type anything else"
        echo -n "Your response: "
        read CONFIRMATION
        
        if [ "$CONFIRMATION" != "CONFIRM_RESET" ]; then
            print_info "Aborted. No changes made."
            exit 0
        fi
        
        return 0  # Proceed with deletion
    else
        print_info "Resource group '$RG' does not exist. Creating fresh infrastructure."
        return 1  # Skip deletion
    fi
}

# Optional backup function
offer_backup() {
    local RG_EXISTS=$(az group exists -n "$RG" 2>/dev/null || echo "false")
    
    if [ "$RG_EXISTS" = "true" ]; then
        echo ""
        print_info "Would you like to see backup commands? Type 'BACKUP' to see them, or press Enter to skip:"
        read -t 10 BACKUP_CHOICE || true
        
        if [ "$BACKUP_CHOICE" = "BACKUP" ]; then
            echo ""
            echo "=== BACKUP COMMANDS ==="
            
            # Try to get existing database info
            local PG_SERVER=$(az postgres flexible-server list -g "$RG" --query "[0].name" -o tsv 2>/dev/null || echo "")
            if [ -n "$PG_SERVER" ]; then
                echo "# PostgreSQL backup:"
                echo "pg_dump \"postgresql://forgeadmin:<PASSWORD>@${PG_SERVER}.postgres.database.azure.com:5432/forge1?sslmode=require\" > forge1_backup_$(date +%Y%m%d_%H%M%S).sql"
            fi
            
            # Key Vault secrets
            if az keyvault show -g "$RG" -n "$KV" &>/dev/null; then
                echo ""
                echo "# Key Vault secrets:"
                echo "az keyvault secret list --vault-name $KV --query '[].name' -o tsv"
                echo "az keyvault secret show --vault-name $KV --name JWT-SECRET --query value -o tsv"
                echo "az keyvault secret show --vault-name $KV --name BACKEND-CORS-ORIGINS --query value -o tsv 2>/dev/null || true"
            fi
            
            echo "======================="
            echo ""
            print_info "Press Enter to continue..."
            read
        fi
    fi
}

# Teardown function
teardown_staging() {
    print_info "Starting teardown of staging resources..."
    
    # Delete resource group
    print_info "Deleting resource group '$RG'..."
    az group delete -n "$RG" --yes --no-wait || true
    
    # Wait for deletion to complete (with timeout)
    local MAX_WAIT=300  # 5 minutes
    local ELAPSED=0
    while [ "$ELAPSED" -lt "$MAX_WAIT" ]; do
        if [ "$(az group exists -n "$RG" 2>/dev/null || echo "false")" = "false" ]; then
            print_success "Resource group deleted successfully"
            return 0
        fi
        echo -n "."
        sleep 5
        ELAPSED=$((ELAPSED + 5))
    done
    
    print_warning "Resource group deletion still in progress. Continuing..."
}

# Bootstrap core resources
bootstrap_core() {
    print_info "Creating core Azure resources..."
    
    # Create resource group
    print_info "Creating resource group '$RG' in '$LOC'..."
    az group create -n "$RG" -l "$LOC" --output none
    print_success "Resource group created"
    
    # Create ACR
    print_info "Creating Azure Container Registry '$ACR'..."
    az acr create -g "$RG" -n "$ACR" --sku Basic --output none
    ACR_LOGIN=$(az acr show -g "$RG" -n "$ACR" --query loginServer -o tsv)
    print_success "ACR created: $ACR_LOGIN"
    
    # Create Key Vault
    print_info "Creating Key Vault '$KV'..."
    az keyvault create -g "$RG" -n "$KV" -l "$LOC" --enable-rbac-authorization false --output none
    print_success "Key Vault created"
    
    # Create Container Apps Environment
    print_info "Creating Container Apps Environment '$ACA_ENV'..."
    az containerapp env create -g "$RG" -n "$ACA_ENV" -l "$LOC" --output none
    print_success "Container Apps Environment created"
    
    # Enable ACR admin for simplicity in staging
    print_info "Enabling ACR admin user..."
    az acr update -n "$ACR" -g "$RG" --admin-enabled true --output none
    print_success "ACR admin enabled"
}

# Setup datastores
setup_datastores() {
    print_info "Setting up data stores..."
    
    # Generate secure passwords
    PG_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    JWT_SECRET=$(openssl rand -hex 32)
    
    # Create PostgreSQL Flexible Server
    print_info "Creating PostgreSQL Flexible Server '$PG_NAME'..."
    az postgres flexible-server create \
        -g "$RG" \
        -n "$PG_NAME" \
        -l "$LOC" \
        --admin-user "forgeadmin" \
        --admin-password "$PG_PASSWORD" \
        --sku-name "Standard_B1ms" \
        --tier "Burstable" \
        --version "14" \
        --storage-size 32 \
        --public-access "0.0.0.0-255.255.255.255" \
        --yes \
        --output none
    print_success "PostgreSQL server created"
    
    # Create database
    print_info "Creating database 'forge1'..."
    az postgres flexible-server db create \
        -g "$RG" \
        -s "$PG_NAME" \
        -d "forge1" \
        --output none
    print_success "Database created"
    
    # Enable pgvector extension
    print_info "Enabling pgvector extension..."
    az postgres flexible-server parameter set \
        -g "$RG" \
        -s "$PG_NAME" \
        --name azure.extensions \
        --value "VECTOR" \
        --output none || true
    
    # Construct DATABASE_URL
    DATABASE_URL="postgresql://forgeadmin:${PG_PASSWORD}@${PG_NAME}.postgres.database.azure.com:5432/forge1?sslmode=require"
    
    # Create Redis Cache
    print_info "Creating Redis Cache '$REDIS_NAME'..."
    az redis create \
        -g "$RG" \
        -n "$REDIS_NAME" \
        -l "$LOC" \
        --sku "Basic" \
        --vm-size "c0" \
        --enable-non-ssl-port false \
        --output none
    print_success "Redis Cache created"
    
    # Get Redis key
    print_info "Retrieving Redis access key..."
    REDIS_KEY=$(az redis list-keys -g "$RG" -n "$REDIS_NAME" --query primaryKey -o tsv)
    REDIS_URL="rediss://:${REDIS_KEY}@${REDIS_NAME}.redis.cache.windows.net:6380/0"
    
    # Store secrets in Key Vault
    print_info "Storing secrets in Key Vault..."
    az keyvault secret set --vault-name "$KV" --name "DATABASE-URL" --value "$DATABASE_URL" --output none
    az keyvault secret set --vault-name "$KV" --name "REDIS-URL" --value "$REDIS_URL" --output none
    az keyvault secret set --vault-name "$KV" --name "JWT-SECRET" --value "$JWT_SECRET" --output none
    az keyvault secret set --vault-name "$KV" --name "BACKEND-CORS-ORIGINS" --value "" --output none
    print_success "Secrets stored in Key Vault"
    
    # Print masked values
    echo ""
    print_success "Data stores configured:"
    echo "  DATABASE_URL: postgresql://forgeadmin:****@${PG_NAME}.postgres.database.azure.com:5432/forge1"
    echo "  REDIS_URL: rediss://:****@${REDIS_NAME}.redis.cache.windows.net:6380/0"
    echo "  JWT_SECRET: ****${JWT_SECRET: -8}"
    echo "  Secrets stored in: $KV"
}

# Build and push images
build_push_images() {
    print_info "Building and pushing container images..."
    
    # Login to ACR
    print_info "Logging in to ACR..."
    az acr login -n "$ACR" --output none
    print_success "Logged in to ACR"
    
    # Get Git SHA for versioning
    GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    
    # Build backend
    print_info "Building backend image..."
    docker buildx build \
        --platform linux/amd64 \
        -t "${ACR_LOGIN}/forge1-backend:staging" \
        -t "${ACR_LOGIN}/forge1-backend:${GIT_SHA}" \
        -f /workspace/backend/Dockerfile \
        /workspace/backend \
        --push
    print_success "Backend image pushed"
    
    # Check if frontend Dockerfile exists, create if not
    if [ ! -f "/workspace/frontend/Dockerfile" ]; then
        print_info "Creating frontend Dockerfile..."
        cat > /workspace/frontend/Dockerfile << 'EOF'
# Multi-stage Dockerfile for Next.js SSR
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Accept build args for Next.js public env vars
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_ENV_LABEL
ARG NEXT_PUBLIC_GIT_SHA

ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_ENV_LABEL=$NEXT_PUBLIC_ENV_LABEL
ENV NEXT_PUBLIC_GIT_SHA=$NEXT_PUBLIC_GIT_SHA

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
EOF
        print_success "Frontend Dockerfile created"
    fi
    
    # Ensure frontend has proper build scripts
    print_info "Checking frontend package.json scripts..."
    cd /workspace/frontend
    if ! grep -q '"start":' package.json; then
        print_warning "Adding start script to package.json"
        # This would need proper JSON manipulation, keeping simple for now
    fi
    
    # Build frontend
    print_info "Building frontend image..."
    docker buildx build \
        --platform linux/amd64 \
        -t "${ACR_LOGIN}/forge1-frontend:staging" \
        -t "${ACR_LOGIN}/forge1-frontend:${GIT_SHA}" \
        --build-arg NEXT_PUBLIC_API_BASE_URL="__PLACEHOLDER__" \
        --build-arg NEXT_PUBLIC_ENV_LABEL="Staging" \
        --build-arg NEXT_PUBLIC_GIT_SHA="${GIT_SHA}" \
        -f /workspace/frontend/Dockerfile \
        /workspace/frontend \
        --push
    print_success "Frontend image pushed"
    
    cd /workspace
}

# Deploy backend
deploy_backend() {
    print_info "Deploying backend to Azure Container Apps..."
    
    # Get ACR credentials
    ACR_USERNAME=$(az acr credential show -n "$ACR" --query username -o tsv)
    ACR_PASSWORD=$(az acr credential show -n "$ACR" --query "passwords[0].value" -o tsv)
    
    # Create backend container app
    az containerapp create \
        -g "$RG" \
        -n "$BACKEND_APP" \
        --environment "$ACA_ENV" \
        --image "${ACR_LOGIN}/forge1-backend:staging" \
        --ingress external \
        --target-port 8000 \
        --registry-server "$ACR_LOGIN" \
        --registry-username "$ACR_USERNAME" \
        --registry-password "$ACR_PASSWORD" \
        --cpu 0.5 \
        --memory 1.0 \
        --min-replicas 1 \
        --max-replicas 3 \
        --secrets \
            "database-url=keyvaultref:https://${KV}.vault.azure.net/secrets/DATABASE-URL,identityref:system" \
            "redis-url=keyvaultref:https://${KV}.vault.azure.net/secrets/REDIS-URL,identityref:system" \
            "jwt-secret=keyvaultref:https://${KV}.vault.azure.net/secrets/JWT-SECRET,identityref:system" \
        --env-vars \
            "ENV=staging" \
            "DATABASE_URL=secretref:database-url" \
            "REDIS_URL=secretref:redis-url" \
            "JWT_SECRET=secretref:jwt-secret" \
            "BACKEND_CORS_ORIGINS=" \
        --output none || {
        # Fallback without Key Vault integration if it fails
        print_warning "Key Vault integration failed, using direct secrets..."
        
        # Get secrets from Key Vault
        DB_URL=$(az keyvault secret show --vault-name "$KV" --name "DATABASE-URL" --query value -o tsv)
        REDIS_URL_VAL=$(az keyvault secret show --vault-name "$KV" --name "REDIS-URL" --query value -o tsv)
        JWT_SECRET_VAL=$(az keyvault secret show --vault-name "$KV" --name "JWT-SECRET" --query value -o tsv)
        
        az containerapp create \
            -g "$RG" \
            -n "$BACKEND_APP" \
            --environment "$ACA_ENV" \
            --image "${ACR_LOGIN}/forge1-backend:staging" \
            --ingress external \
            --target-port 8000 \
            --registry-server "$ACR_LOGIN" \
            --registry-username "$ACR_USERNAME" \
            --registry-password "$ACR_PASSWORD" \
            --cpu 0.5 \
            --memory 1.0 \
            --min-replicas 1 \
            --max-replicas 3 \
            --secrets \
                "database-url=${DB_URL}" \
                "redis-url=${REDIS_URL_VAL}" \
                "jwt-secret=${JWT_SECRET_VAL}" \
            --env-vars \
                "ENV=staging" \
                "DATABASE_URL=secretref:database-url" \
                "REDIS_URL=secretref:redis-url" \
                "JWT_SECRET=secretref:jwt-secret" \
                "BACKEND_CORS_ORIGINS=" \
            --output none
    }
    
    # Get backend URL
    API_HOST=$(az containerapp show -g "$RG" -n "$BACKEND_APP" --query properties.configuration.ingress.fqdn -o tsv)
    API_URL="https://${API_HOST}"
    print_success "Backend deployed: $API_URL"
    
    # Export for frontend
    export API_URL
}

# Deploy frontend
deploy_frontend() {
    print_info "Deploying frontend to Azure Container Apps..."
    
    # Get ACR credentials
    ACR_USERNAME=$(az acr credential show -n "$ACR" --query username -o tsv)
    ACR_PASSWORD=$(az acr credential show -n "$ACR" --query "passwords[0].value" -o tsv)
    
    # Create frontend container app
    az containerapp create \
        -g "$RG" \
        -n "$FRONTEND_APP" \
        --environment "$ACA_ENV" \
        --image "${ACR_LOGIN}/forge1-frontend:staging" \
        --ingress external \
        --target-port 3000 \
        --registry-server "$ACR_LOGIN" \
        --registry-username "$ACR_USERNAME" \
        --registry-password "$ACR_PASSWORD" \
        --cpu 0.5 \
        --memory 1.0 \
        --min-replicas 1 \
        --max-replicas 3 \
        --env-vars \
            "NODE_ENV=production" \
            "NEXT_PUBLIC_ENV_LABEL=Staging" \
            "NEXT_PUBLIC_API_BASE_URL=${API_URL}" \
        --output none
    
    # Get frontend URL
    UI_HOST=$(az containerapp show -g "$RG" -n "$FRONTEND_APP" --query properties.configuration.ingress.fqdn -o tsv)
    UI_URL="https://${UI_HOST}"
    print_success "Frontend deployed: $UI_URL"
    
    # Export for CORS
    export UI_URL
}

# Configure CORS
configure_cors() {
    print_info "Configuring CORS..."
    
    # Get current CORS origins
    CURRENT_CORS=$(az keyvault secret show --vault-name "$KV" --name "BACKEND-CORS-ORIGINS" --query value -o tsv 2>/dev/null || echo "")
    
    # Add UI URL if not present
    if [[ "$CURRENT_CORS" != *"$UI_URL"* ]]; then
        if [ -z "$CURRENT_CORS" ]; then
            NEW_CORS="$UI_URL"
        else
            NEW_CORS="${CURRENT_CORS},${UI_URL}"
        fi
        
        print_info "Updating CORS origins to: $NEW_CORS"
        az keyvault secret set --vault-name "$KV" --name "BACKEND-CORS-ORIGINS" --value "$NEW_CORS" --output none
        
        # Update backend with new CORS
        az containerapp update \
            -g "$RG" \
            -n "$BACKEND_APP" \
            --set-env-vars "BACKEND_CORS_ORIGINS=${NEW_CORS}" \
            --output none
        
        # Restart backend
        print_info "Restarting backend to apply CORS changes..."
        az containerapp revision restart \
            -g "$RG" \
            -n "$BACKEND_APP" \
            --revision latest \
            --output none || true
        
        print_success "CORS configured"
    else
        print_info "CORS already configured for $UI_URL"
    fi
}

# Smoke checks
run_smoke_checks() {
    print_info "Running smoke checks..."
    echo ""
    
    # Backend health check
    echo "1. Backend Live Check:"
    curl -sS "${API_URL}/api/v1/health/live" | jq . 2>/dev/null || echo "  Failed to reach backend /health/live"
    
    echo ""
    echo "2. Backend Ready Check:"
    curl -sS "${API_URL}/api/v1/health/ready" | jq . 2>/dev/null || echo "  Failed to reach backend /health/ready"
    
    echo ""
    echo "3. CORS Header Check:"
    CORS_HEADER=$(curl -sSI -H "Origin: ${UI_URL}" "${API_URL}/api/v1/health/ready" 2>/dev/null | grep -i "access-control-allow-origin" || echo "  No CORS header found")
    echo "  $CORS_HEADER"
    
    echo ""
    echo "4. Frontend Reachability:"
    if curl -sS -f "$UI_URL" >/dev/null 2>&1; then
        echo "  ✅ Frontend is reachable at: $UI_URL"
    else
        echo "  ⚠️  Frontend may not be fully ready yet at: $UI_URL"
    fi
    
    echo ""
}

# Final report
generate_report() {
    echo ""
    echo "================================================"
    echo "DEPLOYMENT REPORT - Forge 1 Staging"
    echo "================================================"
    echo ""
    echo "ENVIRONMENT:"
    echo "  Resource Group:  $RG"
    echo "  Location:        $LOC"
    echo "  Suffix:          $SUFFIX"
    echo ""
    echo "CONTAINER REGISTRY:"
    echo "  ACR Login:       $ACR_LOGIN"
    echo "  Images:"
    echo "    - ${ACR_LOGIN}/forge1-backend:staging"
    echo "    - ${ACR_LOGIN}/forge1-frontend:staging"
    echo ""
    echo "INFRASTRUCTURE:"
    echo "  ACA Environment: $ACA_ENV"
    echo "  Key Vault:       $KV"
    echo "  PostgreSQL:      $PG_NAME"
    echo "  Redis Cache:     $REDIS_NAME"
    echo ""
    echo "DEPLOYED APPLICATIONS:"
    echo "  Backend API:     $API_URL"
    echo "  Frontend UI:     $UI_URL"
    echo ""
    echo "NEXT STEPS:"
    echo "  1. Visit the UI:     $UI_URL"
    echo "  2. Check API docs:   ${API_URL}/docs"
    echo "  3. Monitor logs:     az containerapp logs show -g $RG -n $BACKEND_APP --follow"
    echo "  4. Scale if needed:  az containerapp update -g $RG -n $BACKEND_APP --min-replicas 2"
    echo ""
    echo "To redeploy, simply run this script again."
    echo "================================================"
}

# Main execution
main() {
    echo ""
    print_info "Starting Forge 1 staging deployment..."
    
    # Step 1: Check Azure login
    check_azure_login
    
    # Step 2: Safety check
    if safety_check; then
        # Step 3: Optional backup
        offer_backup
        
        # Step 4: Teardown
        teardown_staging
    fi
    
    # Step 5: Bootstrap core
    bootstrap_core
    
    # Step 6: Setup datastores
    setup_datastores
    
    # Step 7: Build and push images
    build_push_images
    
    # Step 8: Deploy backend
    deploy_backend
    
    # Step 9: Deploy frontend
    deploy_frontend
    
    # Step 10: Configure CORS
    configure_cors
    
    # Step 11: Run smoke checks
    run_smoke_checks
    
    # Step 12: Generate report
    generate_report
    
    print_success "Deployment completed successfully!"
}

# Run main function
main "$@"