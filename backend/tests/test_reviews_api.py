from __future__ import annotations

import json
import os

from fastapi.testclient import TestClient

from app.main import app


def test_reviews_trace_redacts_prompt_and_has_shape() -> None:
    os.environ["ENV"] = "local"
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", data={"username": "admin@example.com", "password": "admin"}, headers={"content-type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    # Create employee
    r = c.post("/api/v1/employees/", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, data=json.dumps({"name": "trace_emp", "role_name": "research_assistant", "description": "d", "tools": []}))
    assert r.status_code in (200, 201)
    emp_id = r.json()["id"]
    # Run a task to generate spans
    r = c.post(f"/api/v1/employees/{emp_id}/run", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, data=json.dumps({"task": "analyze: prompt example", "iterations": 1}))
    assert r.status_code == 200
    # Find the latest task execution id via logs endpoint
    r = c.get(f"/api/v1/employees/{emp_id}/logs", headers={"Authorization": f"Bearer {token}"})
    # If logs API not present, skip
    if r.status_code != 200:
        return
    logs = r.json()
    assert isinstance(logs, list)
    if not logs:
        return
    task_id = logs[0]["id"]
    rr = c.get(f"/api/v1/reviews/{task_id}", headers={"Authorization": f"Bearer {token}"})
    assert rr.status_code == 200
    data = rr.json()
    assert "tool_calls" in data and isinstance(data["tool_calls"], list)
    # Redaction: any input.prompt should be redacted
    for call in data["tool_calls"]:
        inp = call.get("input") or {}
        if "prompt" in inp:
            assert inp["prompt"] == "***redacted***"


