from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.session import get_session
from app.db.models import CanaryConfig, ShadowInvocation
from app.shadow.dispatcher import should_shadow, tee_and_record
from app.shadow.differ import semantic_diff_score


def _db() -> Session:
    for s in get_session():
        return s
    raise RuntimeError("no session")


def test_canary_config_and_diff_scoring() -> None:
    db = _db()
    CanaryConfig.__table__.create(bind=db.get_bind(), checkfirst=True)
    cfg = CanaryConfig(tenant_id="t1", employee_id="e1", shadow_employee_id="e2", percent=100, threshold=0.5, windows=3, status="active")
    db.add(cfg)
    db.commit()
    ok, found = should_shadow(db, tenant_id="t1", employee_id="e1")
    assert ok and found is not None
    score = semantic_diff_score("hello world", "hello world")
    assert score >= 0.99
    corr = tee_and_record(db, tenant_id="t1", employee_id="e1", shadow_employee_id="e2", input_text="hi", primary_output="a", shadow_output="b", score=0.5)
    row = db.query(ShadowInvocation).filter(ShadowInvocation.correlation_id == corr).one_or_none()
    assert row is not None


