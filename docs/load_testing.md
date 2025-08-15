# Load Testing Playbook

This repo includes k6 and Locust scenarios for repeatable load tests.

## Scenarios

- k6:
  - `baseline.js`: steady load (default 10 RPS, 1m)
  - `surge_10x.js`: ramp to ~10x burst
  - `soak_2h.js`: 2 hours steady load (adjustable)
- Locust:
  - `tests/load/locust/locustfile.py` mirrors flows

Flows exercised:
- Auth (dev login) to get JWT
- Run AI task `/api/v1/ai/execute`
- Read metrics `/api/v1/metrics/summary`

## Run locally

```bash
# k6 baseline
FORGE1_API_URL=http://localhost:8000 ./scripts/load/run_k6.sh baseline

# k6 surge
FORGE1_API_URL=http://localhost:8000 RATE=50 ./scripts/load/run_k6.sh surge_10x

# k6 soak (shorten for dev)
FORGE1_API_URL=http://localhost:8000 DURATION=10m ./scripts/load/run_k6.sh soak_2h

# Locust headless
FORGE1_API_URL=http://localhost:8000 USERS=100 SPAWN_RATE=10 DURATION=5m ./scripts/load/run_locust.sh
```

Artifacts:
- k6: JSON summaries in `artifacts/k6_<scenario>_<ts>/summary.json`
- Locust: CSVs in `artifacts/locust_<ts>/results_*.csv`

## Grafana dashboards

Import dashboards JSON and wire to Prometheus/Redis exporters as applicable. A simple p95/errors/RPS/tokens/sec dashboard JSON can be added to your ops Grafana; metrics exposed by Forge 1 are under `/metrics` (Prometheus format) when enabled.

Suggested panels:
- `http_request_duration_seconds` p95
- `http_requests_total` (RPS)
- `http_request_errors_total`
- `forge_tokens_used_total` (if exported)

## Scaling ACA (Azure Container Apps)

- Set min/max replicas to match expected VUs
- Increase CPU/memory per replica according to p95 goals
- Ensure connection pool sizes in env (DB/Redis) match load
- Use ACA revisions for surge testing and rollback
