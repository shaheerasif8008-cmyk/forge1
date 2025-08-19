from __future__ import annotations

import os
import json

from fastapi.testclient import TestClient

from app.main import app


def _login_token(client: TestClient) -> str:
    r = client.post("/api/v1/auth/login", data={"username": "admin@example.com", "password": "admin"}, headers={"content-type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _create_employee(client: TestClient, token: str, name: str = "mem_test_emp") -> str:
    r = client.post(
        "/api/v1/employees/",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data=json.dumps({"name": name, "role_name": "research_assistant", "description": "d", "tools": []}),
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def test_add_and_search_memory() -> None:
    os.environ["ENV"] = "local"
    client = TestClient(app)
    token = _login_token(client)
    emp_id = _create_employee(client, token)

    # Add two memories with distinct content
    r1 = client.post(
        f"/api/v1/employees/{emp_id}/memory/add",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data=json.dumps({"content": "Customer prefers emails in the morning.", "kind": "note"}),
    )
    assert r1.status_code == 200, r1.text

    r2 = client.post(
        f"/api/v1/employees/{emp_id}/memory/add",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data=json.dumps({"content": "Customer's timezone is PST.", "kind": "note"}),
    )
    assert r2.status_code == 200, r2.text

    # Search for "timezone" should rank the timezone fact/event higher than morning
    r3 = client.get(
        f"/api/v1/employees/{emp_id}/memory/search",
        headers={"Authorization": f"Bearer {token}"},
        params={"q": "timezone PST", "top_k": 5},
    )
    assert r3.status_code == 200, r3.text
    data = r3.json()
    assert isinstance(data.get("events"), list)
    assert isinstance(data.get("facts"), list)
    # At least one match should be returned
    assert len(data["events"]) >= 1 or len(data["facts"]) >= 1

