from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app


def _admin_headers(tenant: str = "t-es") -> dict[str, str]:
    tok = create_access_token("1", {"tenant_id": tenant, "roles": ["admin"]})
    return {"Authorization": f"Bearer {tok}"}


def test_list_escalations_empty() -> None:
    c = TestClient(app)
    r = c.get("/api/v1/admin/escalations/?tenant_id=t-es", headers=_admin_headers())
    assert r.status_code == 200
    assert isinstance(r.json(), list)


