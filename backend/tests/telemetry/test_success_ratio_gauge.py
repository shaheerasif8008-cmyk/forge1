from __future__ import annotations

from app.core.telemetry.metrics_service import MetricsService, TaskMetrics, DailyUsageMetric
from app.db.session import SessionLocal


def test_success_ratio_gauge_updated(monkeypatch) -> None:
    # Use a local Redis URL that may not exist; rollup uses DB and gauge setter guarded
    ms = MetricsService(redis_url="redis://localhost:6379/15")
    with SessionLocal() as db:
        # Ensure clean slate
        try:
            DailyUsageMetric.__table__.drop(bind=db.get_bind(), checkfirst=True)
        except Exception:
            pass
        # First call success
        ms.rollup_task(db, TaskMetrics(tenant_id="t-g", employee_id=None, duration_ms=100, tokens_used=10, success=True))
        # Second call failure
        ms.rollup_task(db, TaskMetrics(tenant_id="t-g", employee_id=None, duration_ms=50, tokens_used=5, success=False))
        # Read back success_ratio
        row = db.query(DailyUsageMetric).filter_by(tenant_id="t-g", employee_id=None).first()
        assert row is not None
        assert row.success_ratio is not None
        assert 0.0 <= row.success_ratio <= 1.0

