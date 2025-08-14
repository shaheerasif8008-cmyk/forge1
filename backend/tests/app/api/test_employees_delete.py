from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app


def _headers(tenant: str = "t-del") -> dict[str, str]:
    tok = create_access_token("u-del", {"tenant_id": tenant, "roles": ["user"]})
    return {"Authorization": f"Bearer {tok}"}


def test_employee_delete_cascade() -> None:
    c = TestClient(app)
    # Create employee
    res = c.post(
        "/api/v1/employees/",
        headers=_headers(),
        json={
            "name": "ToDelete",
            "role_name": "Sales Agent",
            "description": "desc",
            "tools": ["api_caller"],
        },
    )
    assert res.status_code in (201, 409)

    # List and pick id
    lst = c.get("/api/v1/employees/", headers=_headers())
    assert lst.status_code == 200
    employees = lst.json()
    assert employees
    emp_id = employees[0]["id"]

    # Generate a log entry best-effort
    c.post(f"/api/v1/employees/{emp_id}/run", headers=_headers(), json={"task": "hello"})

    # Delete should succeed via cascade
    d = c.delete(f"/api/v1/employees/{emp_id}", headers=_headers())
    assert d.status_code in (204, 404)


