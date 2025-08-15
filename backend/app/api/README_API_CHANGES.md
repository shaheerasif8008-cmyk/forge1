### Employee-as-a-Service and BYOC Export

- New model `employee_keys(id, tenant_id, employee_id, prefix, hashed_secret, created_at, status, scopes, expires_at)`

- Admin endpoints (JWT admin required):
  - `POST /api/v1/admin/keys/employees/{employee_id}/keys` → `{ prefix, secret_once, key_id }`
  - `POST /api/v1/admin/keys/keys/{key_id}/revoke` → `{ key_id, status }`
  - `POST /api/v1/admin/keys/keys/{key_id}/rotate` → `{ prefix, secret_once, key_id }`

- Auth header for EaaS invocation:
  - `Employee-Key: EK_<prefix>.<secret>`

- Invoke API (no JWT, Employee-Key required):
  - `POST /api/v1/v1/employees/{id}/invoke` body `{ input, context?, tools?, stream? }` → `{ trace_id, output, tokens_used, latency_ms, model_used, tool_calls? }`

- Export (BYOC):
  - `POST /api/v1/admin/employees/{id}/export` → tar.gz containing `config.yaml`, `runner.py`, `README.md`, `manifest.json`, `signature.txt` (HMAC-SHA256).

### AI Comms & Interconnect

- New SSE endpoint (admin only):
  - `GET /api/v1/admin/ai-comms/events?tenant_id=&employee_id=&type=`
  - Streams CloudEvents envelopes from internal event bus across: `events.core`, `events.tasks`, `events.employees`, `events.ops`, `events.rag`, `events.security`.
  - Returns the last 100 events live; supports client-side filtering via query params.

- New client metrics and live events (tenant-scoped):
  - `GET /api/v1/client/metrics/summary?hours=24` → summary cards + by_day for charts (tenant-scoped)
  - `GET /api/v1/ai-comms/events?token=` → SSE stream filtered by caller tenant; optional `type`/`employee_id`

- RAG upload:
  - `POST /api/v1/rag/upload` with `{ items: [{ type: 'url'|'pdf'|'csv'|'html', url|path, metadata? }, ...] }`
  - Ingests into `LongTermMemory` (pgvector) under caller tenant

- Branding:
  - `GET/POST /api/v1/branding` → simple tenant branding (logo/colors/dark mode) in-memory for now

- Client escalations:
  - `POST /api/v1/client/escalations` → open an escalation ticket scoped to tenant


### Model Router & Admin Overrides

- Cost/latency-aware router with Redis prompt cache (keyed by model/function/user/prompt/tools)
- Env vars:
  - `PROMPT_CACHE_TTL_SECS`, `OPENAI_1K_TOKEN_COST_CENTS`, `CLAUDE_1K_TOKEN_COST_CENTS`, `GEMINI_1K_TOKEN_COST_CENTS`, `OPENROUTER_1K_TOKEN_COST_CENTS`, `ROUTER_FALLBACK_ORDER`

### Self-tuning & Versions

- New endpoints:
  - `POST /api/v1/employees/{id}/tune` body `{ prompt_prefix?, tool_strategy?, notes? }` → creates a new `employee_versions` snapshot, updates active config
  - `POST /api/v1/employees/{id}/rollback/{version}` → sets `employees.active_version_id` and replaces `config` with snapshot
  - `GET /api/v1/employees/{id}/snapshots` → latest `performance_snapshots` for comparisons
- Runtime/context knobs:
  - Orchestrator accepts `prompt_prefix` and `prompt_variants` to try multiple prompts and record `performance_snapshots`
  - Per-task `cost_cents` is logged in `task_executions`
- Admin flags (per-tenant) via `feature_flags`:
  - Force: `router.force_provider_openrouter|openai|claude|gemini`
  - Disable: `router.disable_provider_openrouter|openai|claude|gemini`
- Discovery endpoint:
  - `GET /api/v1/admin/flags/router/flags` → returns supported router override flags


