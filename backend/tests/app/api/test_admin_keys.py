from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app


def _headers_admin(tenant: str = "t-ak") -> dict[str, str]:
    tok = create_access_token("1", {"tenant_id": tenant, "roles": ["admin"]})
    return {"Authorization": f"Bearer {tok}"}


def test_quota_update_and_rotate() -> None:
    c = TestClient(app)
    # create employee under admin tenant
    res = c.post(
        "/api/v1/employees/",
        headers=_headers_admin(),
        json={"name": "KeyEmp", "role_name": "Sales Agent", "description": "d", "tools": ["api_caller"]},
    )
    assert res.status_code in (201, 409)

    lst = c.get("/api/v1/employees/", headers=_headers_admin())
    assert lst.status_code == 200
    eid = lst.json()[0]["id"]

    # rotate key
    r = c.post(f"/api/v1/admin/keys/employee/{eid}/rotate", headers=_headers_admin())
    assert r.status_code == 200

    # update quota
    q = c.patch(
        f"/api/v1/admin/keys/employee/{eid}/quota",
        headers=_headers_admin(),
        json={"daily_tokens_cap": 5000, "rps_limit": 10, "exceed_behavior": "soft"},
    )
    assert q.status_code == 200

    # list usage
    u = c.get(f"/api/v1/admin/keys/employees?tenant_id=t-ak", headers=_headers_admin())
    assert u.status_code == 200
    items = u.json()
    assert isinstance(items, list)

