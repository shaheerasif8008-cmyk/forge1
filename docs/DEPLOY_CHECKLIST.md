## Forge1 Prelaunch Deployment Checklist

This checklist documents deployment paths for Azure Container Apps and GCP Cloud Run, including image push, service deployment, secrets, and smoke tests.

### Prereqs
- Docker installed and logged in to cloud registries
- Backend env configured via Key Vault/Secret Manager
- Postgres and Redis provisioned (or managed services) and connection strings available

### Common
- Version/tag images from repo root
  - Backend: `backend/Dockerfile`
  - Frontend: `frontend/Dockerfile` (or static hosting)
- Tag: `prelaunch-local` before pushing

### Azure Container Apps
1) Build and push images to ACR
```bash
AZURE_ACR=youracr.azurecr.io
docker build -t $AZURE_ACR/forge1-backend:prelaunch -f backend/Dockerfile .
docker push $AZURE_ACR/forge1-backend:prelaunch
```
2) Provision ACA env, Key Vault secrets (JWT, DB URL, REDIS URL, CORS origins)
3) Deploy ACA from yaml
```bash
az containerapp up -n forge1-backend -g rg-forge1 --yaml ./azure/aca-backend.yaml --image $AZURE_ACR/forge1-backend:prelaunch
```
4) Smoke
```bash
bash scripts/azure/smoke_backend.sh https://YOUR-ACA-URL
```

### GCP Cloud Run
1) Build and push to Artifact Registry
```bash
GCP_REGION=us-central1
GCP_REPO=forge1
gcloud builds submit --tag "$GCP_REGION-docker.pkg.dev/$PROJECT_ID/$GCP_REPO/forge1-backend:prelaunch" .
```
2) Secrets in Secret Manager (JWT, DB URL, REDIS URL, CORS)
3) Deploy Cloud Run
```bash
gcloud run deploy forge1-backend \
  --image "$GCP_REGION-docker.pkg.dev/$PROJECT_ID/$GCP_REPO/forge1-backend:prelaunch" \
  --region $GCP_REGION \
  --allow-unauthenticated \
  --set-env-vars ENV=prod \
  --set-secrets JWT_SECRET=projects/$PROJECT_ID/secrets/JWT_SECRET:latest,\
DATABASE_URL=projects/$PROJECT_ID/secrets/DATABASE_URL:latest,\
REDIS_URL=projects/$PROJECT_ID/secrets/REDIS_URL:latest,\
BACKEND_CORS_ORIGINS=projects/$PROJECT_ID/secrets/BACKEND_CORS_ORIGINS:latest
```
4) Smoke
```bash
bash scripts/gcp/smoke_backend.sh https://YOUR-CR-URL
```

### Post-deploy
- Verify `/api/v1/health/live` and `/api/v1/health/ready`
- Run audit: `bash scripts/audit_local.sh` (point API_BASE_URL)
- E2E: create employee, run, memory search, view trace


