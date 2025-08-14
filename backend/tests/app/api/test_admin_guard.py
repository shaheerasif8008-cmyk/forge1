from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app


def _headers_admin(tenant: str = "t-admin") -> dict[str, str]:
    tok = create_access_token("u-admin", {"tenant_id": tenant, "roles": ["admin"]})
    return {"Authorization": f"Bearer {tok}"}


def _headers_user(tenant: str = "t-admin") -> dict[str, str]:
    tok = create_access_token("u-user", {"tenant_id": tenant, "roles": ["user"]})
    return {"Authorization": f"Bearer {tok}"}


def test_admin_flags_guard() -> None:
    c = TestClient(app)
    # Non-admin forbidden
    r_forbid = c.post(
        "/api/v1/admin/flags/set",
        headers=_headers_user(),
        json={"tenant_id": "t-admin", "flag": "f1", "enabled": True},
    )
    assert r_forbid.status_code == 403
    # Admin allowed
    r_ok = c.post(
        "/api/v1/admin/flags/set",
        headers=_headers_admin(),
        json={"tenant_id": "t-admin", "flag": "f1", "enabled": True},
    )
    assert r_ok.status_code == 200


def test_admin_release_guard() -> None:
    c = TestClient(app)
    r_forbid = c.post("/api/v1/admin/release/percent", headers=_headers_user(), json={"percent": 10})
    assert r_forbid.status_code == 403
    r_ok = c.post("/api/v1/admin/release/percent", headers=_headers_admin(), json={"percent": 10})
    assert r_ok.status_code == 200


def test_admin_promotion_guard() -> None:
    c = TestClient(app)
    r_forbid = c.post(
        "/api/v1/admin/beta/promote",
        headers=_headers_user(),
        json={"feature": "beta_templates", "allowlist": []},
    )
    assert r_forbid.status_code == 403

