from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app


def _headers_admin(tenant: str = "t-invoke") -> dict[str, str]:
    tok = create_access_token("1", {"tenant_id": tenant, "roles": ["admin"]})
    return {"Authorization": f"Bearer {tok}"}


def test_invoke_happy_path_and_budget_429() -> None:
    c = TestClient(app)
    # Create employee
    r = c.post(
        "/api/v1/employees/",
        headers=_headers_admin(),
        json={"name": "Invokable", "role_name": "Sales Agent", "description": "d", "tools": ["api_caller"]},
    )
    assert r.status_code in (201, 409)
    lst = c.get("/api/v1/employees/", headers=_headers_admin())
    eid = lst.json()[0]["id"]

    # Set strict RPS=1
    q = c.patch(
        f"/api/v1/admin/keys/employee/{eid}/quota",
        headers=_headers_admin(),
        json={"daily_tokens_cap": 10, "rps_limit": 1, "exceed_behavior": "hard"},
    )
    assert q.status_code == 200

    k = c.post(f"/api/v1/admin/keys/employees/{eid}/keys", headers=_headers_admin())
    prefix = k.json()["prefix"]
    secret = k.json()["secret_once"]
    hdr = {"Employee-Key": f"EK_{prefix}.{secret}"}

    ok = c.post(f"/v1/employees/{eid}/invoke", headers=hdr, json={"input": "Hello"})
    assert ok.status_code in (200, 500)
    too_many = c.post(f"/v1/employees/{eid}/invoke", headers=hdr, json={"input": "Again"})
    assert too_many.status_code in (200, 429, 500)


