from __future__ import annotations

import os

try:
    from celery import Celery  # type: ignore
except Exception:  # pragma: no cover - optional dep in tests
    Celery = None  # type: ignore[assignment]

from testing_app.core.config import settings


broker_url = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6380/1"))
backend_url = os.getenv("CELERY_RESULT_BACKEND", broker_url)

if Celery is not None:
    celery_app = Celery(
        "testing_app",
        broker=broker_url,
        backend=backend_url,
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )
else:
    class _StubCelery:  # pragma: no cover - used only when celery not installed
        def task(self, name: str | None = None, **_: object):
            def decorator(fn):
                def delay(*args, **kwargs):
                    return fn(*args, **kwargs)
                setattr(fn, "delay", delay)
                return fn
            return decorator

    celery_app = _StubCelery()


