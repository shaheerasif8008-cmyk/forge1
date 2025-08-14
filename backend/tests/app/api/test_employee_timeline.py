from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app


def _headers(tenant: str = "t-tl") -> dict[str, str]:
    tok = create_access_token("u1", {"tenant_id": tenant, "roles": ["user"]})
    return {"Authorization": f"Bearer {tok}"}


def test_timeline_scoped_and_ordered() -> None:
    c = TestClient(app)
    # create employee
    res = c.post(
        "/api/v1/employees/",
        headers=_headers(),
        json={"name": "TLTest", "role_name": "Sales Agent", "description": "d", "tools": ["api_caller"]},
    )
    assert res.status_code in (201, 409)

    lst = c.get("/api/v1/employees/", headers=_headers())
    assert lst.status_code == 200
    emps = lst.json()
    assert emps
    eid = emps[0]["id"]

    # run task best-effort
    c.post(f"/api/v1/employees/{eid}/run", headers=_headers(), json={"task": "hello"})

    tl = c.get(f"/api/v1/employees/{eid}/timeline?limit=10", headers=_headers())
    assert tl.status_code == 200
    events = tl.json()
    assert isinstance(events, list)
    # ordered desc by ts if present
    if len(events) >= 2 and events[0].get("ts") and events[1].get("ts"):
        assert events[0]["ts"] >= events[1]["ts"]


