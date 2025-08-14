from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.core.release.rollout import (
    current_mode,
    rollback_now,
    set_canary_allowlist,
    set_canary_percent,
)
from app.main import app


def _admin_headers() -> dict[str, str]:
    tok = create_access_token("admin", {"tenant_id": "t-admin", "roles": ["admin"]})
    return {"Authorization": f"Bearer {tok}"}


def test_rollout_mode_transitions() -> None:
    # Direct service API
    rollback_now()
    assert current_mode()["mode"] == "off"

    set_canary_percent(25)
    cm = current_mode()
    assert cm["mode"] == "percent" and cm["value"] == 25

    set_canary_allowlist(["t1", "t2"])
    cm2 = current_mode()
    assert cm2["mode"] == "allowlist" and cm2["value"] == ["t1", "t2"]

    rollback_now()
    assert current_mode()["mode"] == "off"


def test_admin_release_endpoints() -> None:
    c = TestClient(app)
    # Set percent
    r = c.post("/api/v1/admin/release/percent", headers=_admin_headers(), json={"percent": 10})
    assert r.status_code == 200
    assert current_mode()["mode"] == "percent"

    # Set allowlist
    r2 = c.post(
        "/api/v1/admin/release/allowlist",
        headers=_admin_headers(),
        json={"tenant_ids": ["a", "b"]},
    )
    assert r2.status_code == 200
    assert current_mode()["mode"] == "allowlist"

    # Rollback
    r3 = c.post("/api/v1/admin/release/rollback", headers=_admin_headers())
    assert r3.status_code == 200
    assert current_mode()["mode"] == "off"


