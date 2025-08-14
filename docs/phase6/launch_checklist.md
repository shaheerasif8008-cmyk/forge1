## Forge 1 – Phase 6 Final Launch Checklist

Use this checklist prior to enabling public beta. Validate in staging first, then in prod.

### 1) Secrets and Config
- **Key Vault secrets present**: DATABASE_URL, REDIS_URL, JWT_SECRET, OPENROUTER_API_KEY (if live), optional: PINECONE_API_KEY/WEAVIATE_API_KEY, ELEVENLABS_API_KEY, SENTRY_DSN.
- **No plaintext creds** in CI/CD or deployment specs.
- **CORS**: `BACKEND_CORS_ORIGINS` set to approved domains (not "*").
- **Environment**: `ENV=prod` in prod workloads.

### 2) Budgets, Quotas, and Guards
- **Global caps**: `MAX_TOKENS_PER_REQ`, `LLM_TIMEOUT_SECS` configured for prod.
- **Per-employee budgets** set via Admin Keys/Quotas API (`daily_tokens_cap`, `rps_limit`, `exceed_behavior`).
- **Circuit breaker** operational for LLM/tool calls.
- **Rate limiting** enabled and observed (per-tenant sliding window).
- **Supervisor policies** per tenant (`supervisor_policy`): deny lists, human approval actions, PII strict.
- **Escalations**: validate `/admin/escalations` list/approve/reject/retry (supports `prompt_override`).

### 3) Canary/Release Controls
- **Canary/allowlist off** (not routing unintended traffic) unless intentionally canarying.
- **Feature flags**: confirm required flags on, risky flags off for tenants in scope.

### 4) Observability and Dashboards
- **Structured logs** flowing to Azure Log Analytics or Loki/Promtail in env.
- **Prometheus metrics** scraping OK (RPS, latency, success ratio).
- **Admin monitoring dashboard** green: active employees, success/failure, tokens/day, error logs.
- **Trace IDs** present end‑to‑end (API → RAG → tools → adapters).

### 5) SLOs and Alerts
- **SLOs defined** and agreed:
  - Availability: ≥ 99.9%
  - Median latency (API): ≤ 300 ms
  - P95 task latency: ≤ 5 s
  - Task success ratio: ≥ 98%
- **Alerts configured** for SLO violations and budget overruns.

### 6) Security and Tenancy
- **Tenant isolation** verified in APIs, logs, metrics, and memory.
- **Admin role checks** enforced for all admin endpoints.
- **SSRF protections** enabled on outbound tools.
- **No sensitive data** in logs; PII policies set per tenant.

### 7) Data/Migrations
- **Alembic migrations** applied; tables present (including `task_reviews`, `escalations`, `supervisor_policy`).
- **Tenant data**: non-null `tenant_id` on daily usage metrics; cascades validated for task reviews when employees deleted.
- **pgvector** extension enabled where required.

### 8) CI/CD
- **CI green** for backend, frontend, shared libs, and testing-app.
- **Prod sanity job** confirms Key Vault secrets present and CORS safe.
- **Auto-deploy** to Azure AI Foundry works on merge to `main`.
- **DB pools**: tune via env `DB_POOL_SIZE` (prod 10–20), `DB_MAX_OVERFLOW` (10–20), `DB_POOL_RECYCLE` (1800–3600).

### 9) Final Smoke (Phase 6)
Run `scripts/smoke_phase6.sh` to validate:
- Two tenants created; employee deployed; task executed.
- Low‑score path retried; an escalation exists and can be resolved.
- Costs/tokens and latency within configured caps.

### 10) Go/No‑Go
- Stakeholders reviewed dashboards and SLOs.
- Incident runbooks and on‑call rotation set.
- Rollback plan verified.


