from __future__ import annotations

import json
from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app
from app.db.session import SessionLocal
from app.db.models import RunFailure


def _headers_admin(tenant: str = "t-runs") -> dict[str, str]:
    tok = create_access_token("1", {"tenant_id": tenant, "roles": ["admin"]})
    return {"Authorization": f"Bearer {tok}"}


def test_replay_queues_message(monkeypatch) -> None:
    c = TestClient(app)
    # Insert a failure row
    with SessionLocal() as db:
        rf = RunFailure(tenant_id="t-runs", employee_id="e1", reason="timeout", payload={"task":"hello"})
        db.add(rf)
        db.commit()
        fid = rf.id
    # Mock redis client xadd
    class FakeRedis:
        def __init__(self, *a, **k): pass
        async def xadd(self, stream, fields): return '1-1'
    import app.api.admin_runs as mod
    class FR:
        @staticmethod
        def from_url(*a, **k): return FakeRedis()
    mod.redis = FR  # type: ignore
    r = c.post(f"/api/v1/admin/runs/{fid}/replay", headers=_headers_admin(), json={"reason":"retry"})
    assert r.status_code == 200
    assert r.json()["status"] == "queued"


