.PHONY: dev fmt lint test testing-up testing-down up down migrate seed doctor backend frontend

dev:
	@echo "Starting backend (8000) and frontend (5173)"
	@(
		cd backend && \
		[ -d .venv ] || python -m venv .venv; \
		source .venv/bin/activate && pip install -r requirements.txt && \
		uvicorn app.main:app --host 0.0.0.0 --port 8000 \
	) &
	@(
		cd frontend && npm install && npm run dev \
	)

fmt:
	@echo "Formatting backend with black and sorting imports with ruff"
	@cd backend && source .venv/bin/activate && black . && ruff check . --fix
	@echo "Formatting frontend with prettier (if configured)"
	@cd frontend && npx --yes prettier . --write || true

lint:
	@echo "Linting backend (ruff, mypy)"
	@cd backend && source .venv/bin/activate && ruff check . && mypy app
	@echo "Linting frontend (eslint)"
	@cd frontend && npm run -s lint || true

test:
	@echo "Running backend tests"
	@cd backend && source .venv/bin/activate && pytest -q


up:
	@echo "Starting local Postgres and Redis via docker compose"
	@docker compose -f docker-compose.local.yml up -d

down:
	@echo "Stopping local Postgres and Redis and removing volumes"
	@docker compose -f docker-compose.local.yml down -v

migrate:
	@echo "Running Alembic migrations against local DB"
	@cd backend && SQLALCHEMY_DATABASE_URL="postgresql+psycopg://forge:forge@127.0.0.1:5542/forge1_local" alembic upgrade head

seed:
	@echo "Seeding demo data via app.db.init_db"
	@cd backend && python -m app.db.init_db

doctor:
	@echo "Running Forge1 doctor"
	@python scripts/dev/doctor.py || true

backend:
	@echo "Starting FastAPI dev server on :8000"
	@cd backend && [ -d .venv ] || python -m venv .venv; \
		source .venv/bin/activate && pip install -r requirements.txt && \
		ENV=dev DATABASE_URL="postgresql://forge:forge@127.0.0.1:5542/forge1_local" REDIS_URL="redis://127.0.0.1:6382/0" \
		uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	@echo "Starting Next.js dev server on :5173"
	@cd frontend && npm install && npm run dev


testing-up:
	@echo "Starting testing-app stack on ports 8002/5542/6380"
	@cd testing-app && docker compose -f docker-compose.testing.yml up -d --build

testing-down:
	@echo "Stopping testing-app stack"
	@cd testing-app && docker compose -f docker-compose.testing.yml down -v


