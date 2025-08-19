from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.db.models import Base


class BetaMetric(Base):
    __tablename__ = "beta_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), index=True, nullable=False)
    feature = Column(String(200), index=True, nullable=False)
    status = Column(String(20), index=True, nullable=False)  # pass | fail
    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    ts = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
    extra = Column(JSONB, nullable=True)


def aggregate_metrics(db: Session, tenant_id: str | None = None, feature: str | None = None) -> dict[str, Any]:
    q = db.query(BetaMetric)
    if tenant_id:
        q = q.filter(BetaMetric.tenant_id == tenant_id)
    if feature:
        q = q.filter(BetaMetric.feature == feature)
    rows = q.order_by(BetaMetric.ts.desc()).limit(50).all()

    pass_count = sum(1 for r in rows if r.status == "pass")
    fail_count = sum(1 for r in rows if r.status == "fail")
    latencies = [r.latency_ms for r in rows if r.latency_ms is not None]
    avg_latency = (sum(latencies) / len(latencies)) if latencies else None
    tokens_in = sum(int(r.tokens_in or 0) for r in rows)
    tokens_out = sum(int(r.tokens_out or 0) for r in rows)

    # Very rough token cost estimator placeholder (e.g., $0.000002 per token)
    est_cost_usd = round((tokens_in + tokens_out) * 0.000002, 6)

    return {
        "count": len(rows),
        "pass": pass_count,
        "fail": fail_count,
        "avg_latency_ms": avg_latency,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "est_cost_usd": est_cost_usd,
        "events": [
            {
                "tenant_id": r.tenant_id,
                "feature": r.feature,
                "status": r.status,
                "tokens_in": r.tokens_in,
                "tokens_out": r.tokens_out,
                "latency_ms": r.latency_ms,
                "ts": r.ts.isoformat(),
            }
            for r in rows
        ],
    }


def ensure_table_exists() -> None:
    """No-op placeholder to preserve imports without runtime DDL.

    Alembic manages the lifecycle of the `beta_metrics` table via migrations
    (see revision `5_add_beta_metrics`). This function exists to maintain
    compatibility with callers that previously invoked a runtime DDL helper.
    """
    return None

