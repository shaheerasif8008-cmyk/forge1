from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app


def _headers_admin(tenant: str = "t-privacy") -> dict[str, str]:
    tok = create_access_token("1", {"tenant_id": tenant, "roles": ["admin"]})
    return {"Authorization": f"Bearer {tok}"}


def test_set_and_get_policy() -> None:
    c = TestClient(app)
    r = c.post("/api/v1/privacy/policy", headers=_headers_admin(), json={"chat_ttl_days": 7, "tool_io_ttl_days": 3, "pii_redaction_enabled": True})
    assert r.status_code == 200
    got = c.get("/api/v1/privacy/policy", headers=_headers_admin())
    assert got.json()["chat_ttl_days"] == 7


def test_gdpr_delete_enqueue() -> None:
    c = TestClient(app)
    r = c.post("/api/v1/privacy/gdpr/delete", headers=_headers_admin(), json={"tenant_id": "t-privacy"})
    assert r.status_code == 200
    assert r.json()["status"] == "enqueued"


