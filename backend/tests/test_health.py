from __future__ import annotations

from fastapi.testclient import TestClient
import types

from app.main import app
from app.api import health as health_module


def test_live_happy(monkeypatch):
    client = TestClient(app)

    def ok_db(*args, **kwargs):
        return None

    def ok_redis(*args, **kwargs):
        class _R:
            def ping(self):
                return True

            def close(self):
                return None

        return _R()

    resp = client.get("/api/v1/health")
    assert resp.status_code in (200,)
    body = resp.json()
    assert "status" in body


def test_ready_fail_db(monkeypatch):
    client = TestClient(app)

    class _BadDB:
        def execute(self, *args, **kwargs):
            raise RuntimeError("fail")

    def _dep():
        class _Ctx:
            def __iter__(self):
                yield _BadDB()

        return _Ctx()

    # monkeypatch get_session dependency via direct import
    monkeypatch.setattr(health_module, "get_session", _dep)
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body.get("db") is False

from fastapi.testclient import TestClient

from app.main import app


def test_health_live() -> None:
    client = TestClient(app)
    res = client.get("/api/v1/health/live")
    assert res.status_code == 200
    assert res.json() == {"status": "live"}


def test_health_ready_shape() -> None:
    client = TestClient(app)
    res = client.get("/api/v1/health/ready")
    # OK in dev/local even if services down; ensure JSON shape has status and trace_id
    assert res.status_code in (200, 503)
    payload = res.json()
    assert "status" in payload
    assert "trace_id" in payload
    # readiness now includes migrations field
    assert "migrations" in payload
