from __future__ import annotations

import os
from fastapi.testclient import TestClient

from app.main import app


def test_login_fallback_dev_only(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "dev")
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", data={"username": "nouser", "password": "admin"})
    assert r.status_code == 200
    assert r.json().get("access_token")


def test_login_fallback_forbidden_in_prod(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "prod")
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", data={"username": "nouser", "password": "admin"})
    assert r.status_code == 403

