# forge1

Minimal monorepo for Forge 1 Lite MVP.

## Structure
- `backend/`: FastAPI backend
- `frontend/`: React + TypeScript frontend
- `infra/`: Infra tooling/scripts

## Quickstart
- Backend
  - `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
  - From repo root: `uvicorn --app-dir backend app.main:app --host 0.0.0.0 --port 8000`
  - API docs: `http://localhost:8000/docs`
- Frontend
  - `cd frontend && npm install && npm run dev`
  - App: `http://localhost:5173`

## Makefile
- `make dev` – start backend and frontend
- `make fmt` – format code
- `make lint` – lint code
- `make test` – run tests

## Pre-commit hooks
Install and enable hooks to lint/format on commit:

```bash
pip install pre-commit
pre-commit install
```

