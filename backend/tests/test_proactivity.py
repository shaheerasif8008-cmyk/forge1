from __future__ import annotations

import os
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.db.models import TaskExecution
from app.proactivity.scheduler import _scan_and_act  # type: ignore[attr-defined]


def test_proactivity_creates_demo_task() -> None:
    os.environ["ENV"] = "local"
    os.environ["PROACTIVITY_ENABLED"] = "true"
    os.environ["SCHEDULE_PERIOD_SEC"] = "60"

    c = TestClient(app)
    # authenticate and create an employee to ensure target exists
    r = c.post("/api/v1/auth/login", data={"username": "admin@example.com", "password": "admin"}, headers={"content-type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    r = c.post(
        "/api/v1/employees/",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"name": "proactive_emp", "role_name": "research_assistant", "description": "d", "tools": []},
    )
    assert r.status_code in (200, 201)

    # Run scan once (synchronously)
    _scan_and_act()

    # Verify that a proactive TaskExecution exists
    with SessionLocal() as db:
        row = db.query(TaskExecution).filter(TaskExecution.task_type == "proactive:auto").order_by(TaskExecution.id.desc()).first()
        assert row is not None
        assert row.success is True


def test_scheduler_does_not_perform_runtime_ddl(monkeypatch) -> None:
    calls: dict[str, int] = {"ddl": 0}

    def fake_begin(*args, **kwargs):
        class _Conn:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, *a, **k):
                sql = str(a[0]) if a else ""
                if "ALTER TABLE" in sql or "CREATE TABLE" in sql or "DROP TABLE" in sql:
                    calls["ddl"] += 1
        return _Conn()

    # Patch engine.begin to track DDL attempts
    import app.db.session as sess
    monkeypatch.setattr(sess.engine, "begin", fake_begin)

    _scan_and_act()

    assert calls["ddl"] == 0


