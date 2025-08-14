## Forge 1 — Azure Ops Pack (Staging via Azure Container Apps)

### Prerequisites
- az, docker, jq, psql installed and on PATH
- `az login` completed and correct subscription selected
- Permissions to create Resource Group, ACR, Key Vault, Log Analytics, Container Apps

Quick check:
```bash
bash scripts/azure/05_check_prereqs.sh
```

### One-liner (staging deploy)
```bash
bash scripts/azure/run_staging.sh
```

The orchestrator will:
- Register providers, bootstrap core resources, optionally create Postgres/Redis
- Prompt for and seed Key Vault secrets
- Build and push the backend image to ACR
- Deploy the Container App and run a smoke test

### Required secrets (Key Vault)
- `OPENROUTER-API-KEY`: from OpenRouter account
- `DATABASE-URL`: e.g. `postgresql://<user>:<pass>@<host>:5432/forge`
- `REDIS-URL`: e.g. `redis://<host>:6379/0`
- `JWT-SECRET`: strong random string (64+ chars recommended)
- `BACKEND-CORS-ORIGINS`: comma-separated allowed origins (no `*` in non-dev)

### Find the backend FQDN and configure frontend
```bash
source .azure/env.staging
az containerapp show -g "$RG" -n forge1-backend --query properties.configuration.ingress.fqdn -o tsv
```
Use `https://<fqdn>` as the API base URL (e.g., set frontend `VITE_API_BASE_URL`). If you change allowed origins, update `BACKEND-CORS-ORIGINS` in Key Vault and restart the app.

### Where to get values for secrets
- OpenRouter key: from your OpenRouter dashboard
- Database URL: use an existing Postgres or run `15_create_datastores.sh --create-pg`
- Redis URL: use an existing Redis or run `15_create_datastores.sh --create-redis`
- JWT secret: generate long random (e.g. `python - <<'PY'\nimport secrets; print(secrets.token_urlsafe(64))\nPY`)
- CORS origins: your frontend origins, e.g. `https://app.example.com,https://staging.example.com`

### Troubleshooting
- Provider registration stuck: rerun `00_register_providers.sh`; check `az provider show`
- ACR auth: `az acr login -n <ACR>`; if needed `docker login <loginServer>`
- Key Vault permissions: ensure the managed identity has `get,list` on secrets
- CORS/401s: set `BACKEND_CORS_ORIGINS` to exact origins; set `JWT_SECRET` in Key Vault
- Port mismatch: backend listens on 8000; Container App ingress targets port 8000

### CI/CD (GitHub Actions)

Provide these repository secrets:
- `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_SUBSCRIPTION_ID` for OIDC Azure login
- `AZURE_SWA_TOKEN` for Static Web Apps deploy
- `STAGING_API_URL` for frontend build-time API base (e.g., `https://<backend-fqdn>`)

Flow:
- Push to `main` → Backend workflow builds in ACR using `az acr build`, updates Container App image, fetches FQDN, runs smoke test (fails CI on errors)
- Push to `main` → Frontend workflow builds with `VITE_API_URL=${{ secrets.STAGING_API_URL }}` and deploys to Azure Static Web Apps


