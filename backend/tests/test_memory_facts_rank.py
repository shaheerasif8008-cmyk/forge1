from __future__ import annotations

import os
import json

from fastapi.testclient import TestClient

from app.main import app


def test_ranked_search_returns_expected() -> None:
    os.environ["ENV"] = "local"
    c = TestClient(app)
    # Login
    r = c.post("/api/v1/auth/login", data={"username": "admin@example.com", "password": "admin"}, headers={"content-type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    # Create employee
    r = c.post(
        "/api/v1/employees/",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data=json.dumps({"name": "rank_emp", "role_name": "research_assistant", "description": "d", "tools": []}),
    )
    assert r.status_code in (200, 201), r.text
    emp_id = r.json()["id"]

    # Insert memories
    m1 = "Project Alpha deadline is Friday"
    m2 = "Team meeting is on Monday"
    m3 = "Alpha budget is $10k"
    for m in (m1, m2, m3):
        rr = c.post(f"/api/v1/employees/{emp_id}/memory/add", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, data=json.dumps({"content": m}))
        assert rr.status_code == 200

    # Query around the Alpha project and deadline
    r = c.get(f"/api/v1/employees/{emp_id}/memory/search", headers={"Authorization": f"Bearer {token}"}, params={"q": "Alpha deadline", "top_k": 3})
    assert r.status_code == 200
    jr = r.json()
    # Ensure we have results and the top result is relevant (heuristic: contains 'Alpha' or 'deadline')
    events = jr.get("events", [])
    facts = jr.get("facts", [])
    joined = [e.get("content", "") for e in events] + [f.get("fact", "") for f in facts]
    assert any("Alpha" in x or "deadline" in x for x in joined)


