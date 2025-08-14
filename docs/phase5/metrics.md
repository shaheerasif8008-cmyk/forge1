### Phase 5: Metrics Collection (Usage Analytics & Performance)

This document outlines the metrics collection system implemented in the Forge 1 backend.

### Goals

- Track per-tenant and per-employee usage:
  - Tasks run, average duration, token consumption, tool calls, errors
- Provide admin-facing `/api/v1/metrics` endpoint
- Persist daily rollups in PostgreSQL
- Maintain hot counters in Redis for quick reads
- Expose Prometheus metrics: requests/sec, average latency, task success ratio

### Components

- `app/core/telemetry/metrics_service.py`
  - `DailyUsageMetric` (Postgres model)
  - `MetricsService` with methods:
    - `incr_task(TaskMetrics)` and `incr_tool_call(tenant_id, employee_id)` in Redis
    - `rollup_task(db, TaskMetrics)` and `rollup_tool_call(db, tenant_id, employee_id)` in Postgres
  - `TaskMetrics` dataclass describing a completed task
- `app/core/telemetry/prom_metrics.py`
  - Global Prometheus collectors: `REQUESTS_TOTAL`, `REQUEST_LATENCY_SECONDS`, `TASK_SUCCESS_RATIO`
  - Helpers: `observe_request`, `set_success_ratio`
- `app/api/metrics.py`
  - `GET /api/v1/metrics`: Admin-only aggregation query with optional filters (`year`, `month`, `tenant_id`, `employee_id`)
  - `GET /api/v1/metrics/prometheus`: Admin-only Prometheus text-format export

### Data model (PostgreSQL)

- Table: `daily_usage_metrics`
  - Keys: `day`, `tenant_id`, `employee_id`
  - Fields: `tasks`, `total_duration_ms`, `total_tokens`, `tool_calls`, `errors`, `avg_duration_ms`, `success_ratio`, `updated_at`
  - Unique constraint on (`day`, `tenant_id`, `employee_id`)

### Hot counters (Redis)

String keys incremented for quick stats:
- `metrics:tenant:{tenant_id}:tasks`
- `metrics:tenant:{tenant_id}:tokens`
- `metrics:tenant:{tenant_id}:duration_ms`
- `metrics:tenant:{tenant_id}:errors`
- `metrics:tenant:{tenant_id}:tool_calls`
- and corresponding `metrics:employee:{employee_id}:*`

### Instrumentation points

- Request middleware (`app/main.py`):
  - Records Prometheus `forge1_requests_total` and `forge1_request_latency_seconds`
- Orchestrator (`ai_orchestrator.py`):
  - On task completion or failure: increments Redis counters per tenant/employee
- Employee runs (`app/api/employees.py`) and generic AI execute (`app/api/ai.py`):
  - Roll up results into Postgres daily usage metrics
- Tools (`api_caller`, `web_scraper`):
  - Increment per-tenant tool call counters

### Prometheus

- Prometheus text endpoint: `GET /api/v1/metrics/prometheus` (admin-only)
- Default registry is used; scrape target should point at the backend service
- Example Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: "forge1-backend"
    metrics_path: /api/v1/metrics/prometheus
    static_configs:
      - targets: ["backend:8000"]
```

### Admin metrics API

- `GET /api/v1/metrics`: returns summary and daily rows
  - Query params: `year`, `month`, `tenant_id`, `employee_id`

### Notes

- The service tolerates missing tables in local/dev and will attempt to create them when rolling up
- Redis failures degrade gracefully (warnings only)
- Success ratio gauge (`TASK_SUCCESS_RATIO`) is available for external calculators; summaries also return success ratios


