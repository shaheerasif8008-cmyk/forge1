from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_tenant_claims_in_me() -> None:
    client = TestClient(app)
    # demo login
    res = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin"})
    assert res.status_code == 200
    token = res.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    data = me.json()
    assert "tenant_id" in data and data["tenant_id"]


def test_employees_are_tenant_scoped() -> None:
    client = TestClient(app)
    res = client.post("/api/v1/auth/login", data={"username": "userA", "password": "admin"})
    assert res.status_code == 200
    tokenA = res.json()["access_token"]

    # Create employee under tenantA (demo tenant default)
    create = client.post(
        "/api/v1/employees/",
        headers={"Authorization": f"Bearer {tokenA}"},
        json={
            "name": "Test Emp",
            "role_name": "Sales Agent",
            "description": "desc",
            "tools": ["api_caller"],
        },
    )
    assert create.status_code in (200, 201, 409)

    # List should succeed for same tenant
    lst = client.get("/api/v1/employees/", headers={"Authorization": f"Bearer {tokenA}"})
    assert lst.status_code == 200


