# Backend – Forge 1

## Run locally (Docker Compose)

1. Copy env template:

```bash
cp .env.example .env
```

2. Start services:

```bash
docker compose up --build
```

3. Verify health:

```bash
curl -s http://localhost:8000/health/live
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health/ready
```

## Run locally (host)

- Ensure Postgres and Redis are running locally and update `.env` values if needed.
- Install deps and run:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Uvicorn command

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
