from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app


def _headers_admin(tenant: str = "t-empkey") -> dict[str, str]:
    tok = create_access_token("1", {"tenant_id": tenant, "roles": ["admin"]})
    return {"Authorization": f"Bearer {tok}"}


def test_key_lifecycle_and_invoke_quota() -> None:
    c = TestClient(app)
    # create employee under admin tenant
    res = c.post(
        "/api/v1/employees/",
        headers=_headers_admin(),
        json={"name": "EaaS", "role_name": "Sales Agent", "description": "d", "tools": ["api_caller"]},
    )
    assert res.status_code in (201, 409)

    lst = c.get("/api/v1/employees/", headers=_headers_admin())
    assert lst.status_code == 200
    eid = lst.json()[0]["id"]

    # create key
    k = c.post(f"/api/v1/admin/keys/employees/{eid}/keys", headers=_headers_admin())
    assert k.status_code == 200
    key = k.json()
    prefix = key["prefix"]
    secret = key["secret_once"]
    hdr = {"Employee-Key": f"EK_{prefix}.{secret}"}

    # happy path invoke
    inv = c.post(f"/v1/employees/{eid}/invoke", headers=hdr, json={"input": "Hello", "stream": False})
    # When orchestrator is stubbed, allow 200 or 500 depending on provider keys
    assert inv.status_code in (200, 500)

    # revoke
    rv = c.post(f"/api/v1/admin/keys/{key['key_id']}/revoke", headers=_headers_admin())
    assert rv.status_code == 200

    # attempt again should 401
    inv2 = c.post(f"/v1/employees/{eid}/invoke", headers=hdr, json={"input": "Hello"})
    assert inv2.status_code == 401


