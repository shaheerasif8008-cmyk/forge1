from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.core.telemetry.beta_metrics import BetaMetric, ensure_table_exists
from app.db.session import SessionLocal
from app.main import app


def _admin_headers() -> dict[str, str]:
    tok = create_access_token("admin", {"tenant_id": "t-admin", "roles": ["admin"]})
    return {"Authorization": f"Bearer {tok}"}


def test_promote_happy_path() -> None:
    # Seed metrics 90% pass
    ensure_table_exists()
    with SessionLocal() as db:
        # Clean previous metrics for isolation
        db.query(BetaMetric).filter(BetaMetric.feature == "beta_templates").delete()
        for i in range(10):
            db.add(
                BetaMetric(
                    tenant_id=f"t{i%3}",
                    feature="beta_templates",
                    status="pass" if i < 9 else "fail",
                    tokens_in=10,
                    tokens_out=5,
                    latency_ms=100,
                )
            )
        db.commit()

    c = TestClient(app)
    r = c.post(
        "/api/v1/admin/beta/promote",
        headers=_admin_headers(),
        json={"feature": "beta_templates", "min_pass_rate": 90, "allowlist": ["t1", "t2"]},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


def test_promote_rejects_on_low_pass_rate() -> None:
    ensure_table_exists()
    with SessionLocal() as db:
        db.query(BetaMetric).filter(BetaMetric.feature == "beta_templates").delete()
        db.add(BetaMetric(tenant_id="t1", feature="beta_templates", status="fail"))
        db.commit()

    c = TestClient(app)
    r = c.post(
        "/api/v1/admin/beta/promote",
        headers=_admin_headers(),
        json={"feature": "beta_templates", "min_pass_rate": 90, "allowlist": ["t1"]},
    )
    assert r.status_code == 400


def test_demote_endpoint() -> None:
    c = TestClient(app)
    r = c.post(
        "/api/v1/admin/beta/demote",
        headers=_admin_headers(),
        json={"feature": "beta_templates", "tenant_ids": ["t1", "t2"]},
    )
    assert r.status_code == 200


