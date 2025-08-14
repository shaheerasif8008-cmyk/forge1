from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.main import app


def test_seed_and_run_sync() -> None:
    os.environ["TESTING"] = "1"  # run synchronously
    client = TestClient(app)
    r = client.post("/api/v1/seed")
    assert r.status_code == 200
    suite_id = r.json()["suite_id"]

    r2 = client.post("/api/v1/runs", json={"suite_id": suite_id, "target_api_url": "http://localhost:8000"})
    assert r2.status_code == 200
    data = r2.json()
    run_id = data["run_id"]
    # if sync, we get result
    r3 = client.get(f"/api/v1/runs/{run_id}")
    assert r3.status_code == 200
    jr = r3.json()
    assert "report_html" in jr


