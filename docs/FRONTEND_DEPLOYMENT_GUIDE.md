# Frontend Deployment Guide - Full-Stack Connectivity Fix

## Overview
This guide provides step-by-step instructions to diagnose and fix the Client Portal UI connectivity issues with the backend API in Azure Container Apps.

## Prerequisites

### Required Tools
- Azure CLI (`az`) - [Install Guide](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- Docker - [Install Guide](https://docs.docker.com/get-docker/)
- Git
- Node.js 20+ (for local testing)

### Azure Resources Required
- Resource Group
- Azure Container Registry (ACR)
- Azure Key Vault
- Azure Container Apps Environment
- Backend Container App deployed

## Quick Start

### 1. Environment Setup

First, ensure you have the Azure environment configured:

```bash
# Login to Azure
az login

# Run the bootstrap script if not already done
bash scripts/azure/10_bootstrap_core.sh

# Verify environment
bash scripts/azure/test_env.sh
```

### 2. Run the Diagnostic and Fix Script

The main script handles all aspects of the deployment:

```bash
# Run the comprehensive diagnostic and fix script
bash scripts/azure/diagnose_fix_frontend.sh
```

This script will:
1. Load Azure context and derive all necessary names
2. Perform connectivity probes
3. Verify and fix environment variables
4. Update CORS configuration in Key Vault
5. Rebuild and push the frontend Docker image
6. Deploy/update the Azure Container App
7. Run smoke tests
8. Provide detailed diagnostics

## Manual Steps (if needed)

### Building the Frontend Image Manually

```bash
# Source environment variables
source .azure/env.staging

# Get ACR login server
ACR_LOGIN=$(az acr show -g "$RG" -n "$ACR" --query loginServer -o tsv)

# Login to ACR
az acr login -n "$ACR"

# Build and push image
docker buildx build --platform linux/amd64 \
  -t "$ACR_LOGIN/forge1-frontend:staging" \
  --build-arg NEXT_PUBLIC_API_BASE_URL="https://your-backend-url" \
  --build-arg NEXT_PUBLIC_ENV_LABEL="Staging" \
  --build-arg NEXT_PUBLIC_GIT_SHA="$(git rev-parse --short HEAD)" \
  -f frontend/Dockerfile frontend --push
```

### Updating CORS Manually

```bash
# Get current CORS value
CORS_VALUE=$(az keyvault secret show --vault-name "$KV" \
  --name "BACKEND-CORS-ORIGINS" --query value -o tsv)

# Add new origin
NEW_CORS="${CORS_VALUE},https://your-frontend-url"

# Update Key Vault
az keyvault secret set --vault-name "$KV" \
  --name "BACKEND-CORS-ORIGINS" --value "$NEW_CORS" -o none

# Restart backend
az containerapp revision restart -g "$RG" -n "forge1-backend-v2"
```

### Deploying Container App Manually

```bash
# Create new Container App
az containerapp create \
  -n "forge1-frontend-${SUFFIX}" \
  -g "$RG" \
  --environment "$ACA_ENV" \
  --image "$ACR_LOGIN/forge1-frontend:staging" \
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
    NEXT_PUBLIC_API_BASE_URL="https://your-backend-url" \
    NEXT_PUBLIC_ENV_LABEL=Staging
```

## Architecture Changes Made

### 1. Next.js Configuration
- Changed from static export (`output: "export"`) to standalone mode (`output: "standalone"`)
- This enables SSR/hybrid rendering required for Azure Container Apps

### 2. Dockerfile
- Multi-stage build for optimized image size
- Proper handling of build-time environment variables
- Respects PORT environment variable for Azure Container Apps
- Non-root user for security

### 3. Package.json
- Updated start script to respect PORT environment variable: `next start -p ${PORT:-3000}`

## Troubleshooting

### Common Issues and Solutions

#### 1. Frontend Returns 404/500
**Symptom**: UI URL returns error status codes

**Solution**:
```bash
# Check container logs
az containerapp logs show -g "$RG" -n "forge1-frontend-${SUFFIX}" --tail 200

# Check revision status
az containerapp revision list -g "$RG" -n "forge1-frontend-${SUFFIX}" -o table
```

#### 2. CORS Errors in Browser
**Symptom**: Browser console shows CORS errors

**Solution**:
```bash
# Verify CORS configuration
curl -sSI -H "Origin: https://your-frontend-url" \
  "https://your-backend-url/api/v1/health/ready" | grep -i "access-control"

# Update CORS if needed (see manual steps above)
```

#### 3. Dashboard Widgets Empty
**Symptom**: UI loads but dashboard shows no data

**Possible Causes**:
- Wrong NEXT_PUBLIC_API_BASE_URL
- User not authenticated
- No data in database

**Solution**:
```bash
# Check environment variables
az containerapp show -g "$RG" -n "forge1-frontend-${SUFFIX}" \
  --query 'properties.template.containers[0].env' -o table

# Test API endpoint directly
curl "https://your-backend-url/api/v1/employees" \
  -H "Authorization: Bearer <your-jwt-token>"
```

#### 4. Build Fails
**Symptom**: Docker build fails

**Solution**:
```bash
# Ensure you're in the workspace root
cd /workspace

# Clean build cache
docker buildx prune -f

# Try building without cache
docker buildx build --no-cache --platform linux/amd64 \
  -t test-build -f frontend/Dockerfile frontend
```

## Environment Variables Reference

### Build-time Variables (baked into image)
- `NEXT_PUBLIC_API_BASE_URL`: Backend API URL
- `NEXT_PUBLIC_ENV_LABEL`: Environment label (e.g., "Staging")
- `NEXT_PUBLIC_GIT_SHA`: Git commit SHA for versioning

### Runtime Variables (Container App)
- `NODE_ENV`: Should be "production"
- `PORT`: Port number (Azure sets this automatically)

## Security Considerations

1. **No Wildcard CORS**: Never use `*` for CORS origins in production
2. **Secure Secrets**: All sensitive values stored in Azure Key Vault
3. **Non-root Container**: Dockerfile uses non-root user
4. **HTTPS Only**: All endpoints use HTTPS

## Validation Checklist

After deployment, verify:

- [ ] Frontend URL returns HTTP 200
- [ ] Backend health check returns "ready"
- [ ] CORS headers present for UI origin
- [ ] Authentication works (login form)
- [ ] Dashboard displays data
- [ ] No console errors in browser DevTools

## Next Steps

1. **Monitor Application**:
   ```bash
   # View metrics
   az monitor metrics list --resource-id \
     "/subscriptions/<sub>/resourceGroups/$RG/providers/Microsoft.App/containerApps/forge1-frontend-${SUFFIX}"
   ```

2. **Scale as Needed**:
   ```bash
   # Update scaling rules
   az containerapp update -g "$RG" -n "forge1-frontend-${SUFFIX}" \
     --min-replicas 2 --max-replicas 10
   ```

3. **Setup CI/CD**:
   - Configure GitHub Actions or Azure DevOps
   - Automate image builds and deployments

## Support

If issues persist after following this guide:

1. Collect diagnostic information:
   ```bash
   bash scripts/azure/diagnose_fix_frontend.sh > diagnostic_output.txt 2>&1
   ```

2. Check all logs:
   - Container App logs
   - Browser console logs
   - Network tab in DevTools

3. Verify all prerequisites are met

## Summary

The diagnostic script (`diagnose_fix_frontend.sh`) is idempotent and safe to run multiple times. It will:
- Detect and fix configuration issues
- Only rebuild images when necessary
- Provide clear error messages and remediation steps
- Output a comprehensive summary of the deployment state

For a quick health check at any time:
```bash
bash scripts/azure/test_env.sh
```