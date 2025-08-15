from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app


def _headers_admin(tenant: str = "t-page") -> dict[str, str]:
    tok = create_access_token("1", {"tenant_id": tenant, "roles": ["admin"]})
    return {"Authorization": f"Bearer {tok}"}


def test_employees_pagination_bounds() -> None:
    c = TestClient(app)
    # First page
    r = c.get("/api/v1/employees", headers=_headers_admin(), params={"page": 1, "page_size": 20})
    assert r.status_code == 200
    data = r.json()
    assert "items" in data and "total" in data and data["page"] == 1
    # Large page_size should clamp
    r2 = c.get("/api/v1/employees", headers=_headers_admin(), params={"page": 1, "page_size": 1000})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["page_size"] <= 100


