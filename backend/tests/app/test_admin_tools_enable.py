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


def test_list_registry_and_enable_tool(client: TestClient):
    token = _login(client)
    r = client.get("/api/v1/admin/tools/registry", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    tools = r.json()
    assert any(t["name"] == "csv_reader" for t in tools)
    # Enable slack_notifier without config should fail schema (requires webhook_url)
    r2 = client.post(
        "/api/v1/admin/tools/slack_notifier/enable",
        headers={"Authorization": f"Bearer {token}"},
        json={"enabled": True, "config": {}},
    )
    assert r2.status_code == 400
    # Enable csv_reader should succeed without config
    r3 = client.post(
        "/api/v1/admin/tools/csv_reader/enable",
        headers={"Authorization": f"Bearer {token}"},
        json={"enabled": True, "config": {}},
    )
    assert r3.status_code == 200
    jr = r3.json()
    assert jr["tool_name"] == "csv_reader" and jr["enabled"] is True


