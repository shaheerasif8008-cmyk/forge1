from __future__ import annotations

import hmac
import hashlib
from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app


def _admin_headers(tenant: str = "t-hook") -> dict[str, str]:
    tok = create_access_token("1", {"tenant_id": tenant, "roles": ["admin"]})
    return {"Authorization": f"Bearer {tok}"}


def test_webhook_crud_and_test_queue():
    c = TestClient(app)
    # Create endpoint
    r = c.post("/api/v1/webhooks/", headers=_admin_headers(), json={"url": "https://example.com/webhook", "secret": "s3cr3t", "active": True})
    assert r.status_code == 200
    eid = r.json()["id"]
    # Send test event
    r2 = c.post("/api/v1/webhooks/test", headers=_admin_headers(), json={"event_type": "unit.test", "data": {"x": 1}})
    assert r2.status_code == 200


def test_signature_verification():
    c = TestClient(app)
    payload = {"event_type": "unit.test", "data": {"x": 1}}
    secret = "topsecret"
    mac = hmac.new(secret.encode("utf-8"), digestmod=hashlib.sha256)
    mac.update(("payload:" + str(payload)).encode("utf-8"))
    sig = f"sha256={mac.hexdigest()}"
    r = c.post("/api/v1/webhooks/verify", json=payload, params={"signature": sig, "secret": secret})
    assert r.status_code == 200
    assert r.json()["valid"] is True


