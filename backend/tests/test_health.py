from fastapi.testclient import TestClient

from app.main import app


def test_health_live() -> None:
    client = TestClient(app)
    res = client.get("/api/v1/health/live")
    assert res.status_code == 200
    assert res.json() == {"status": "live"}
