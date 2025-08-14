from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_run_suite_default_golden() -> None:
    client = TestClient(app)
    r = client.post("/suites/run", params={"suite": "golden_basic"})
    assert r.status_code == 200
    data = r.json()
    assert data["suite_name"].lower().startswith("golden")
    assert data["failed"] == 0
