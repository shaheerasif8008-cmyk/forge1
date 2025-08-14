### Phase 5: Structured Logging and Traceability (Backend)

This document describes the structured logging and trace ID propagation implemented in the Forge 1 backend and AI orchestration layer.

### Goals

- Unified, JSON-structured logs across API, orchestrator, RAG, tools, and runtime
- Request-scoped trace ID (correlation ID) injected at ingress and propagated downstream
- Tenant-aware fields for multi-tenant debugging
- Compatible with Azure Monitor and Prometheus-aligned log pipelines (e.g., Promtail → Loki)

### What was added

- `app/core/logging_config.py`: centralized logging configuration and context utilities
  - JSON formatter output fields:
    - `timestamp`, `level`, `logger`, `message`, `module`, `function`, `line`
    - `trace_id`, `tenant_id`, `user_id`, `request_method`, `request_path`, `app`
  - Context management via `contextvars` with helpers:
    - `configure_logging()`, `generate_trace_id()`, `set_request_context()`, `clear_request_context()`, `get_trace_id()`
  - Context manager `use_request_context(...)` for scoped updates
- Request middleware in `app/main.py`:
  - Extracts `X-Request-ID`/`X-Correlation-ID` or generates a UUID
  - Parses JWT for `tenant_id`/`user_id`, sets request context
  - Adds `X-Trace-ID` response header
  - Emits start/end logs and persists an `AuditLog` record (best-effort)
- Instrumentation hooks:
  - Orchestrator: task start/end, RAG usage, errors
  - RAG: adding documents, retrieval source, reranking
  - Tools: `api_caller`, `web_scraper` request/response and errors; headers propagate `X-Trace-ID`
  - Runtime: iteration start/end, completion
  - API: `ai.execute`, `employees.run` attach `trace_id` into responses where helpful

### Environment

- `LOG_LEVEL`: logging verbosity, defaults to `INFO`. Supported: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
- `ENV`: environment name, used elsewhere; not required for logging.

### Example JSON log line

```json
{
  "timestamp": "2025-01-01T12:00:00+00:00",
  "level": "INFO",
  "logger": "app.core.orchestrator.ai_orchestrator",
  "message": "Task completed in 0.42s using openai-gpt-5",
  "module": "ai_orchestrator",
  "function": "run_task",
  "line": 305,
  "trace_id": "a1b2c3d4e5f6...",
  "tenant_id": "tenantA",
  "user_id": "123",
  "request_method": "POST",
  "request_path": "/api/v1/ai/execute",
  "app": "forge1-backend"
}
```

### Trace ID propagation

- Incoming requests: `X-Request-ID` or `X-Correlation-ID` honored; otherwise a new UUID is generated
- Response header: `X-Trace-ID` is always emitted
- Downstream calls: LLM adapters, tools, and document fetchers include `X-Trace-ID` header when present
- Orchestrator context: embeds `trace_id` into `context` map so internal components can forward it further

### Consuming logs

- Azure Monitor (Container Apps/AKS): JSON logs written to stdout/stderr are collected automatically when configured. Parse fields as JSON for queries and dashboards.
- Prometheus ecosystem:
  - Prometheus primarily handles metrics; for logs use Promtail → Grafana Loki. Promtail scrapes container stdout and ships JSON logs; Loki stores/searches; Grafana visualizes.
  - Suggested pipeline: Docker/Kubernetes stdout → Promtail (JSON pipeline stage) → Loki → Grafana.

Minimal Promtail pipeline snippet (values.yaml):

```yaml
scrape_configs:
  - job_name: forge1-backend
    static_configs:
      - targets: [localhost]
        labels:
          job: forge1-backend
          __path__: /var/log/containers/*forge1-backend*.log
    pipeline_stages:
      - json:
          expressions:
            level: level
            trace_id: trace_id
            tenant_id: tenant_id
            message: message
      - labels:
          level:
          tenant_id:
          trace_id:
```

### FastAPI integration points

- Middleware in `app/main.py` sets/clears request context and logs start/end
- Audit logs persisted to `audit_logs` table with `trace_id` and duration

### Local testing

1) Start backend as usual (uvicorn). Make a request:

```bash
curl -H "Authorization: Bearer <token>" -H "X-Request-ID: test-123" \
  -d '{"task":"hello"}' -H 'Content-Type: application/json' \
  http://localhost:8000/api/v1/ai/execute
```

2) Observe JSON logs in console; `X-Trace-ID` will be included in the response headers.

### Notes

- Uvicorn/SQLAlchemy logs are normalized to use the same root handler
- All logs are plain JSONL to stdout for compatibility with cloud log collectors
- Avoid logging secrets; the middleware redacts common sensitive query params


