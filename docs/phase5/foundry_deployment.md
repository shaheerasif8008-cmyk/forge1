### Phase 5: Azure AI Foundry Deployment

This guide describes deploying the Forge 1 backend and orchestration engine to Azure AI Foundry.

### Prerequisites

- Azure subscription with AI Foundry workspace and resource group
- Azure Container Registry (ACR)
- Azure Key Vault with secrets:
  - `database-url`, `redis-url`, `jwt-secret`, and optional `openai-api-key`
- GitHub repository secrets configured:
  - `AZURE_CREDENTIALS` (JSON for service principal with subscriptionId, tenantId, clientId, clientSecret)
  - `AZURE_RG`, `AZURE_FOUNDRY_WS`, `ACR_NAME`, `KEYVAULT_NAME`

### Container build and push

- Dockerfile: `backend/Dockerfile`
- Script: `deploy/foundry/acr_push.sh`

Manual example:

```bash
./deploy/foundry/acr_push.sh <acr_name> forge1-backend v1
```

### Foundry deployment

- Spec template: `deploy/foundry/foundry_deploy.json`
- Script: `deploy/foundry/foundry_deploy.sh`

Manual example:

```bash
./deploy/foundry/foundry_deploy.sh <rg> <workspace> forge1-backend <acr_name> <kv_name> <tag>
```

The template wires environment variables from Key Vault and sets autoscale rules. Ports expose 8000.

### CI/CD (GitHub Actions)

- Workflow: `.github/workflows/ci-prod.yml` builds, pushes, and deploys on merges to `main`:
  - Builds/pushes `forge1-backend:${{ github.sha }}` to ACR
  - Calls `foundry_deploy.sh` with the same tag

### Autoscaling

- `foundry_deploy.json` contains simple autoscale rules (CPU and requests-per-second). Adjust thresholds as needed.

### Environment configuration

- Secrets are referenced via Key Vault in the deployment spec. Add/rotate in Key Vault without code changes.


