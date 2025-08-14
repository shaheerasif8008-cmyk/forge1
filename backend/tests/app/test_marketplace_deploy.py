from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _login(client: TestClient) -> str:
    r = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_marketplace_list_and_deploy(client: TestClient):
    token = _login(client)
    r = client.get("/api/v1/marketplace/templates", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(t["key"] == "lead_qualifier" for t in data)
    r2 = client.post(
        "/api/v1/marketplace/templates/lead_qualifier/deploy",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code in (200, 201)
    out = r2.json()
    assert out["employee_id"] and out["name"]


