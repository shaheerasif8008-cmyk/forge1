FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl gcc libpq-dev && rm -rf /var/lib/apt/lists/*

FROM base AS builder
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --prefix=/install -r requirements.txt

FROM base AS runtime
RUN useradd -m appuser
WORKDIR /app
# Ensure migration files and config are present explicitly
# Ensure migration files and config are present explicitly
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY --from=builder /install /usr/local
COPY . /app
# Include container-native migrate script at a stable path (source is backend/scripts)
COPY scripts/migrate_in_container.sh /app/scripts/migrate_in_container.sh
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]


