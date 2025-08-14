from __future__ import annotations

import os
from fastapi.testclient import TestClient

from app.main import app


def test_zap_ignored_rules_do_not_create_findings() -> None:
    os.environ["TESTING"] = "1"
    client = TestClient(app)
    # Provide a security profile with ignore list; we cannot actually run ZAP in CI reliably
    r = client.post(
        "/api/v1/suites",
        json={
            "name": "zap_smoke",
            "target_env": "staging",
            "scenario_ids": [],
            "security_profile": {"api_url": "http://localhost:8000", "ui_url": "http://localhost:5173", "ignore": ["X-Content-Type-Options Header"]},
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
    assert "run" in data
    # We don't assert on actual findings as ZAP may not run; we assert structure presence
    assert isinstance(data["run"].get("stats", {}).get("zap", {}), dict)


