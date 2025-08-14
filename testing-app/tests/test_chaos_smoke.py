from __future__ import annotations

import os
from fastapi.testclient import TestClient

from app.main import app


def test_chaos_start_and_teardown() -> None:
    os.environ["TESTING"] = "1"
    client = TestClient(app)

    # Create a minimal suite with chaos_profile simulate=true to avoid requiring Toxiproxy in CI
    r = client.post(
        "/api/v1/suites",
        json={
            "name": "chaos_smoke",
            "target_env": "staging",
            "scenario_ids": [],
            "chaos_profile": {"simulate": True, "latency_ms": 300, "loss_pct": 1},
            "load_profile": {"tool": "k6", "duration": "1s", "rate": 1, "endpoints": ["/health"]},
        },
        headers={"X-Testing-Service-Key": os.getenv("TESTING_SERVICE_KEY", "")},
    )
    assert r.status_code == 200
    suite_id = r.json()["id"]

    rr = client.post(
        "/api/v1/runs",
        json={"suite_id": suite_id, "target_api_url": "http://localhost:8000"},
        headers={"X-Testing-Service-Key": os.getenv("TESTING_SERVICE_KEY", "")},
    )
    assert rr.status_code == 200
    run_id = rr.json()["run_id"]
    g = client.get(f"/api/v1/runs/{run_id}", headers={"X-Testing-Service-Key": os.getenv("TESTING_SERVICE_KEY", "")})
    assert g.status_code == 200
    data = g.json()
    stats = data["run"].get("stats", {})
    assert "chaos" in stats and stats["chaos"].get("enabled") is True


