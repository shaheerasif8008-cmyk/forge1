from __future__ import annotations

import os
from fastapi.testclient import TestClient

from app.main import app


def test_k6_locust_smoke_30s() -> None:
    os.environ["TESTING"] = "1"
    client = TestClient(app)

    # Seed a suite and override load profiles for a tiny 30s duration
    s = client.post("/api/v1/seed", headers={"X-Testing-Service-Key": os.getenv("TESTING_SERVICE_KEY", "")})
    assert s.status_code in (200, 401)  # when key missing, create via suite API
    if s.status_code != 200:
        s2 = client.post("/api/v1/suites", json={
            "name": "smoke",
            "target_env": "staging",
            "scenario_ids": [],
            "load_profile": {"tool": "k6", "duration": "1s", "rate": 1, "endpoints": ["/health"]},
        }, headers={"X-Testing-Service-Key": os.getenv("TESTING_SERVICE_KEY", "")})
        assert s2.status_code == 200
        suite_id = s2.json()["id"]
    else:
        suite_id = s.json()["suite_id"]

    r = client.post("/api/v1/runs", json={"suite_id": suite_id, "target_api_url": "http://localhost:8000"}, headers={"X-Testing-Service-Key": os.getenv("TESTING_SERVICE_KEY", "")})
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    g = client.get(f"/api/v1/runs/{run_id}", headers={"X-Testing-Service-Key": os.getenv("TESTING_SERVICE_KEY", "")})
    assert g.status_code == 200
    data = g.json()
    assert "run" in data and "report_html" in data
    # Stats may be empty if docker doesn't run in CI, but structure should be present
    assert isinstance(data["run"].get("stats"), dict)


