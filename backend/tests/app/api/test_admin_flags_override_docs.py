from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app


def _headers_admin(tenant: str = "t-flags") -> dict[str, str]:
    tok = create_access_token("1", {"tenant_id": tenant, "roles": ["admin"]})
    return {"Authorization": f"Bearer {tok}"}


def test_router_flags_docs() -> None:
    c = TestClient(app)
    r = c.get("/api/v1/admin/flags/router/flags", headers=_headers_admin())
    assert r.status_code == 200
    data = r.json()
    assert "force" in data and "disable" in data


