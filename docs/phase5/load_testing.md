### Phase 5: Load Testing and Performance Tuning

This guide explains how we simulate high load for Forge 1 and summarize performance results and optimizations.

### Goals

- Simulate 100 concurrent employees
- Achieve ~1,000 tasks per minute
- Measure avg response time, error rate, and resource utilization

### Tools

- Locust (Python): `tests/load/locustfile.py`
- k6 (JS): `tests/load/k6_script.js`

### Running Locust

Prereqs: `pip install locust`

```bash
export FORGE_API_URL=http://localhost:8000
export FORGE_TOKEN=<jwt>
locust -f tests/load/locustfile.py --headless -u 100 -r 20 -t 10m
```

Flags:
- `-u 100`: simulate 100 concurrent users
- `-r 20`: spawn rate
- `-t 10m`: test duration

### Running k6

Prereqs: install k6

```bash
FORGE_API_URL=http://localhost:8000 FORGE_TOKEN=<jwt> k6 run tests/load/k6_script.js
```

The script defines a `constant-arrival-rate` scenario targeting ~1000 tasks/minute.

### Metrics to collect

- Response times (p50/p95/p99)
- Error rate
- CPU/memory of backend containers (Azure Monitor or `docker stats` in local)
- DB stats (pg_stat_statements), Redis ops/sec

### Optimizations applied

- Database connection pool tuning (see `app/db/session.py`):
  - `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE`
- Redis usage improvements for rate limiting and metrics (pipeline usage where appropriate)
- Worker concurrency: scale replicas via Foundry autoscaling; set uvicorn workers (`--workers`) if needed

### Results (example placeholders)

- Baseline (single replica, pool 10/20):
  - Avg latency: 220ms, p95: 600ms
  - Error rate: 1.2% (mostly 429/timeout)
  - CPU: 65%, Mem: 1.1GiB
- Tuned (2 replicas, pool 20/40):
  - Avg latency: 140ms, p95: 320ms
  - Error rate: 0.4%
  - CPU: 55% per replica, Mem: 0.9GiB

Adapt these with real measurements from your environment.


