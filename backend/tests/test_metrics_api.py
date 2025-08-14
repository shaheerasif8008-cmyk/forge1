from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app


def _auth_headers(tenant_id: str = "t1") -> dict[str, str]:
    tok = create_access_token("u1", {"tenant_id": tenant_id, "roles": ["user"]})
    return {"Authorization": f"Bearer {tok}"}


def test_metrics_ingest_and_query() -> None:
    c = TestClient(app)
    # ingest a few
    for status in ("pass", "fail", "pass"):
        r = c.post(
            "/api/v1/metrics/beta",
            headers=_auth_headers("t1"),
            json={
                "tenant_id": "t1",
                "feature": "beta_templates",
                "status": status,
                "tokens_in": 10,
                "tokens_out": 5,
                "latency_ms": 123,
            },
        )
        assert r.status_code == 200

    q = c.get("/api/v1/metrics/beta", headers=_auth_headers("t1"))
    assert q.status_code == 200
    data = q.json()
    assert data["count"] >= 3
    assert "events" in data and isinstance(data["events"], list)


def test_metrics_cross_tenant_forbidden() -> None:
    c = TestClient(app)
    # Auth for tenant t1 but attempt to write for t2
    r = c.post(
        "/api/v1/metrics/beta",
        headers=_auth_headers("t1"),
        json={
            "tenant_id": "t2",
            "feature": "beta_templates",
            "status": "pass",
        },
    )
    assert r.status_code == 403

    # Seed one event under t1
    ok = c.post(
        "/api/v1/metrics/beta",
        headers=_auth_headers("t1"),
        json={
            "tenant_id": "t1",
            "feature": "beta_templates",
            "status": "pass",
        },
    )
    assert ok.status_code == 200

    # Auth as t2 should be forbidden to read t1 metrics
    q_forbidden = c.get(
        "/api/v1/metrics/beta?tenant_id=t1",
        headers=_auth_headers("t2"),
    )
    assert q_forbidden.status_code == 403


