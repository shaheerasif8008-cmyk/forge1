from __future__ import annotations

"""Metrics service for usage analytics and performance monitoring.

Responsibilities:
- Real-time counters in Redis (per-tenant/employee tasks, tool calls, errors)
- Persistent daily rollups in Postgres (per-tenant/employee)
- Prometheus metrics export (requests/sec, avg latency, success ratio)
"""

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from redis import Redis
from sqlalchemy import Column, Date, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Session

from ..config import settings
from ...db.models import Base
from ...interconnect import get_interconnect
from ...interconnect.cloudevents import make_event

logger = logging.getLogger(__name__)


# ---------- Postgres rollup model ----------


class DailyUsageMetric(Base):
    __tablename__ = "daily_usage_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    day = Column(Date, index=True, nullable=False)
    tenant_id = Column(String(100), index=True, nullable=False)
    employee_id = Column(String(100), index=True, nullable=True)

    tasks = Column(Integer, nullable=False, default=0)
    total_duration_ms = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    tool_calls = Column(Integer, nullable=False, default=0)
    errors = Column(Integer, nullable=False, default=0)

    avg_duration_ms = Column(Float, nullable=True)
    success_ratio = Column(Float, nullable=True)

    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        UniqueConstraint("day", "tenant_id", "employee_id", name="uq_daily_usage_metric"),
    )


# ---------- Service API ----------


@dataclass
class TaskMetrics:
    tenant_id: str
    employee_id: str | None
    duration_ms: int
    tokens_used: int
    success: bool


class MetricsService:
    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or settings.redis_url

    def _redis(self) -> Redis:
        return Redis.from_url(self._redis_url, decode_responses=True)

    # --- Real-time Redis counters ---
    def incr_task(self, m: TaskMetrics) -> None:
        try:
            r = self._redis()
            # Per-tenant and per-employee counters
            r.incrby(f"metrics:tenant:{m.tenant_id}:tasks", 1)
            if m.employee_id:
                r.incrby(f"metrics:employee:{m.employee_id}:tasks", 1)
            r.incrby(f"metrics:tenant:{m.tenant_id}:tokens", max(0, int(m.tokens_used)))
            if m.employee_id:
                r.incrby(f"metrics:employee:{m.employee_id}:tokens", max(0, int(m.tokens_used)))
            r.incrby(f"metrics:tenant:{m.tenant_id}:duration_ms", max(0, int(m.duration_ms)))
            if m.employee_id:
                r.incrby(
                    f"metrics:employee:{m.employee_id}:duration_ms", max(0, int(m.duration_ms))
                )
            if not m.success:
                r.incrby(f"metrics:tenant:{m.tenant_id}:errors", 1)
                if m.employee_id:
                    r.incrby(f"metrics:employee:{m.employee_id}:errors", 1)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Redis metrics increment failed: {e}")
        # Publish budget/metrics related events for internal AIs (best-effort)
        try:
            import asyncio as _asyncio
            async def _emit():
                ic = await get_interconnect()
                await ic.publish(
                    stream="events.core",
                    type="metrics.task",
                    source="metrics_service",
                    data={
                        "tenant_id": m.tenant_id,
                        "employee_id": m.employee_id,
                        "duration_ms": m.duration_ms,
                        "tokens_used": m.tokens_used,
                        "success": m.success,
                    },
                    tenant_id=m.tenant_id,
                    employee_id=m.employee_id,
                )
                if not m.success:
                    await ic.publish(
                        stream="events.ops",
                        type="task.failed",
                        source="metrics_service",
                        tenant_id=m.tenant_id,
                        employee_id=m.employee_id,
                        data={"reason": "llm_error"},
                    )
            _asyncio.create_task(_emit())
        except Exception:
            pass

    def incr_tool_call(self, tenant_id: str, employee_id: str | None) -> None:
        try:
            r = self._redis()
            r.incrby(f"metrics:tenant:{tenant_id}:tool_calls", 1)
            if employee_id:
                r.incrby(f"metrics:employee:{employee_id}:tool_calls", 1)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Redis tool call increment failed: {e}")

    def incr_actor_run(self, actor: str) -> None:
        """Increment run counters per internal AI actor for rate limiting/monitoring."""
        try:
            r = self._redis()
            r.incrby(f"metrics:actor:{actor}:runs", 1)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Redis actor increment failed: {e}")

    # --- Postgres daily rollups ---
    @staticmethod
    def _today() -> date:
        return datetime.now(UTC).date()

    def rollup_task(self, db: Session, m: TaskMetrics) -> None:
        """Upsert daily aggregates for a completed task."""
        day = self._today()
        try:
            # Ensure table exists (safe in dev/CI)
            DailyUsageMetric.__table__.create(bind=db.get_bind(), checkfirst=True)

            row = (
                db.query(DailyUsageMetric)
                .filter(
                    DailyUsageMetric.day == day,
                    DailyUsageMetric.tenant_id == m.tenant_id,
                    DailyUsageMetric.employee_id == (m.employee_id or None),
                )
                .first()
            )
            if row is None:
                row = DailyUsageMetric(
                    day=day,
                    tenant_id=m.tenant_id,
                    employee_id=m.employee_id,
                    tasks=0,
                    total_duration_ms=0,
                    total_tokens=0,
                    tool_calls=0,
                    errors=0,
                    avg_duration_ms=None,
                    success_ratio=None,
                )
                db.add(row)

            row.tasks += 1
            row.total_duration_ms += max(0, int(m.duration_ms))
            row.total_tokens += max(0, int(m.tokens_used))
            if not m.success:
                row.errors += 1
            # Derive metrics
            row.avg_duration_ms = (row.total_duration_ms / row.tasks) if row.tasks else 0.0
            successes = max(0, row.tasks - row.errors)
            row.success_ratio = (successes / row.tasks) if row.tasks else 0.0
            row.updated_at = datetime.now(UTC)
            db.commit()
            # Update Prometheus success ratio gauge
            try:
                from .prom_metrics import set_success_ratio

                set_success_ratio(m.tenant_id, m.employee_id, float(row.success_ratio or 0.0))
            except Exception:
                pass
        except Exception as e:  # noqa: BLE001
            db.rollback()
            logger.warning(f"Postgres rollup failed: {e}")

    def rollup_tool_call(self, db: Session, tenant_id: str, employee_id: str | None) -> None:
        day = self._today()
        try:
            DailyUsageMetric.__table__.create(bind=db.get_bind(), checkfirst=True)
            row = (
                db.query(DailyUsageMetric)
                .filter(
                    DailyUsageMetric.day == day,
                    DailyUsageMetric.tenant_id == tenant_id,
                    DailyUsageMetric.employee_id == (employee_id or None),
                )
                .first()
            )
            if row is None:
                row = DailyUsageMetric(
                    day=day,
                    tenant_id=tenant_id,
                    employee_id=employee_id,
                    tasks=0,
                    total_duration_ms=0,
                    total_tokens=0,
                    tool_calls=0,
                    errors=0,
                )
                db.add(row)
            row.tool_calls += 1
            row.updated_at = datetime.now(UTC)
            db.commit()
        except Exception as e:  # noqa: BLE001
            db.rollback()
            logger.warning(f"Postgres tool rollup failed: {e}")

    # --- Prometheus metrics ---
    # Deprecated: use prom_metrics module for collectors


