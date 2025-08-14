from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.core.flags.feature_flags import FeatureFlag, set_flag
from app.db.session import SessionLocal, engine
from app.db.models import Tenant
from app.main import app


def _ensure_tables() -> None:
    insp = inspect(engine)
    if "tenants" not in insp.get_table_names():
        Tenant.__table__.create(bind=engine, checkfirst=True)
    if "feature_flags" not in insp.get_table_names():
        FeatureFlag.__table__.create(bind=engine, checkfirst=True)


def _seed_tenant(tenant_id: str, beta: bool) -> None:
    with SessionLocal() as db:
        t = db.get(Tenant, tenant_id)
        if t is None:
            t = Tenant(id=tenant_id, name=f"Tenant {tenant_id}")
            setattr(t, "beta", beta)
            db.add(t)
        else:
            setattr(t, "beta", beta)
        db.commit()


def _clear_flags() -> None:
    with SessionLocal() as db:
        FeatureFlag.__table__.create(bind=engine, checkfirst=True)
        db.query(FeatureFlag).delete()
        db.commit()


def test_beta_gate_returns_404_when_flag_disabled() -> None:
    _ensure_tables()
    _clear_flags()
    client = TestClient(app)

    _seed_tenant("tenant_beta", beta=True)

    from app.api.auth import create_access_token

    tok = create_access_token("u1", {"tenant_id": "tenant_beta", "roles": ["user"]})
    res = client.get("/api/v1/beta/templates", headers={"Authorization": f"Bearer {tok}"})
    assert res.status_code == 404


def test_beta_gate_allows_when_flag_enabled() -> None:
    _ensure_tables()
    _clear_flags()
    client = TestClient(app)

    _seed_tenant("tenant_beta2", beta=True)
    with SessionLocal() as db:
        set_flag(db, "tenant_beta2", "beta_templates", True)

    from app.api.auth import create_access_token

    tok = create_access_token("u1", {"tenant_id": "tenant_beta2", "roles": ["user"]})
    res = client.get("/api/v1/beta/templates", headers={"Authorization": f"Bearer {tok}"})
    assert res.status_code == 200
    assert "templates" in res.json()


