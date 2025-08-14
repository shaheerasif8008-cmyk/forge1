# Forge 1 Testing App (Sandbox)

Isolated FastAPI service for running synthetic suites with shared harness.

## Isolation

- DB: `forge1_testing` (Postgres), separate container/port
- Redis: DB 1 on port 6380
- Vector namespace prefix: `testing_`
- HTTP port: 8002 (avoid prod 8000)

## Quick start (Docker Compose)

```bash
cd testing-app
cp env.testing.example .env.testing  # optional; compose sets defaults
docker compose -f docker-compose.testing.yml up -d --build
curl http://localhost:8002/health
```

## Local dev

```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -e ../shared
uvicorn app.main:app --reload --port 8002
```

## Endpoints

- `GET /health` – basic health and env echo
- Legacy:
  - `GET /suites/` – list available suites
  - `POST /suites/run?suite=golden_basic.yaml` – run a suite via shared runner (default mocked executor)
- New testing_app APIs (prefix `/api/v1`):
  - `POST /api/v1/scenarios` – create scenario
  - `GET /api/v1/scenarios` – list scenarios
  - `POST /api/v1/suites` – create suite
  - `POST /api/v1/runs` – create run `{suite_id, target_api_url?}`
  - `GET /api/v1/runs/{id}` – get run status, signed report paths
  - `POST /api/v1/runs/{id}/abort` – abort running
  - `POST /api/v1/seed` – seed baseline suite

### Start services

```bash
uvicorn app.main:app --reload --port 8002
celery -A testing_app.worker.celery_app.celery_app worker -l INFO
```

### Sample curl

```bash
# Seed baseline
curl -s -X POST http://localhost:8002/api/v1/seed | jq

# Create run (sync in tests with TESTING=1)
curl -s -X POST http://localhost:8002/api/v1/runs \
  -H 'Content-Type: application/json' \
  -d '{"suite_id": 1, "target_api_url": "http://localhost:8000"}' | jq

# Get run
curl -s http://localhost:8002/api/v1/runs/1 | jq
```

## Tests

```bash
pytest -q
```


