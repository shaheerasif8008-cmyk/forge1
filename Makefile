.PHONY: dev fmt lint test

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


