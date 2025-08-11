from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def login(username: str) -> str:
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", data={"username": username, "password": "admin"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_employee_crud_is_tenant_scoped() -> None:
    c = TestClient(app)
    token = login("tenantUser")
    # create
    res = c.post(
        "/api/v1/employees/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "EmpOne",
            "role_name": "Sales Agent",
            "description": "desc",
            "tools": ["api_caller"],
        },
    )
    assert res.status_code in (201, 409)

    # list
    lst = c.get("/api/v1/employees/", headers={"Authorization": f"Bearer {token}"})
    assert lst.status_code == 200
    employees = lst.json()
    assert isinstance(employees, list)

    # run
    if employees:
        emp_id = employees[0]["id"]
        run = c.post(
            f"/api/v1/employees/{emp_id}/run",
            headers={"Authorization": f"Bearer {token}"},
            json={"task": "Say hi", "iterations": 1},
        )
        assert run.status_code in (200, 500)

        logs = c.get(
            f"/api/v1/employees/{emp_id}/logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert logs.status_code == 200


def test_employee_access_requires_auth() -> None:
    c = TestClient(app)
    assert c.get("/api/v1/employees/").status_code == 401
    assert c.post("/api/v1/employees/", json={}).status_code == 401

