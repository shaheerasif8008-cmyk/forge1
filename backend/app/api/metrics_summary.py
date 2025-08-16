from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, case, cast, Integer
from sqlalchemy.orm import Session

from ..db.models import AuditLog, TaskExecution
from .auth import get_current_user
from ..db.session import get_session


router = APIRouter(prefix="/metrics", tags=["metrics-dashboard"])


class SummaryPoint(BaseModel):
    day: str
    tasks: int
    avg_duration_ms: float | None = None
    success_ratio: float | None = None
    tokens: int | None = None
    errors: int


class SummaryResponse(BaseModel):
    tasks: int
    avg_duration_ms: float | None = None
    success_ratio: float | None = None
    tokens: int | None = None
    cost_cents: int | None = None
    by_day: list[SummaryPoint]


@router.get("/summary", response_model=SummaryResponse)
def metrics_summary(
    hours: int = Query(default=24, ge=1, le=24 * 30),
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> SummaryResponse:
    tenant_id = str(current_user["tenant_id"])
    since = datetime.now(UTC) - timedelta(hours=hours)

    # Aggregate totals
    q_totals = select(
        func.count(TaskExecution.id),
        func.avg(TaskExecution.execution_time),
        func.avg(cast(TaskExecution.success, Integer)),
        func.coalesce(func.sum(TaskExecution.tokens_used), 0),
        func.coalesce(func.sum(TaskExecution.cost_cents), 0),
    ).where(
        TaskExecution.tenant_id == tenant_id,
        TaskExecution.created_at >= since,
    )
    total_tasks, avg_ms, success_ratio, tokens, cost_cents = db.execute(q_totals).one()

    # Per-day breakdown (UTC)
    day = func.date_trunc("day", TaskExecution.created_at)
    q_days = (
        select(
            day.label("day"),
            func.count(TaskExecution.id),
            func.avg(TaskExecution.execution_time),
            func.avg(cast(TaskExecution.success, Integer)),
            func.coalesce(func.sum(TaskExecution.tokens_used), 0),
            func.coalesce(
                func.sum(case((TaskExecution.success.is_(False), 1), else_=0)),
                0,
            ),
        )
        .where(TaskExecution.tenant_id == tenant_id, TaskExecution.created_at >= since)
        .group_by(day)
        .order_by(day.asc())
    )
    by_day: list[SummaryPoint] = []
    for d, cnt, avg_dur, succ, tok, errs in db.execute(q_days).all():
        by_day.append(
            SummaryPoint(
                day=d.date().isoformat(),
                tasks=int(cnt or 0),
                avg_duration_ms=float(avg_dur) if avg_dur is not None else None,
                success_ratio=float(succ) if succ is not None else None,
                tokens=int(tok or 0),
                errors=int(errs or 0),
            )
        )

    return SummaryResponse(
        tasks=int(total_tasks or 0),
        avg_duration_ms=float(avg_ms) if avg_ms is not None else None,
        success_ratio=float(success_ratio) if success_ratio is not None else None,
        tokens=int(tokens or 0) if tokens is not None else None,
        cost_cents=int(cost_cents or 0) if cost_cents is not None else None,
        by_day=by_day,
    )


class TrendPoint(BaseModel):
    ts: str
    tasks: int
    success_ratio: float | None = None
    avg_duration_ms: float | None = None


@router.get("/trends")
def metrics_trends(
    hours: int = Query(default=24, ge=1, le=24 * 7),
    bucket_minutes: int = Query(default=60, ge=5, le=24 * 60),
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> dict[str, list[TrendPoint]]:
    tenant_id = str(current_user["tenant_id"])
    since = datetime.now(UTC) - timedelta(hours=hours)

    # Use hour buckets for >=60, minute for smaller to keep SQL simple and portable
    trunc_unit = "hour" if bucket_minutes >= 60 else "minute"
    bucket = func.date_trunc(trunc_unit, TaskExecution.created_at)

    q = (
        select(
            bucket.label("bucket"),
            func.count(TaskExecution.id),
            func.avg(cast(TaskExecution.success, Integer)),
            func.avg(TaskExecution.execution_time),
        )
        .where(TaskExecution.tenant_id == tenant_id, TaskExecution.created_at >= since)
        .group_by("bucket")
        .order_by("bucket")
    )

    points: list[TrendPoint] = []
    for ts, cnt, succ, avg_dur in db.execute(q).all():
        points.append(
            TrendPoint(
                ts=ts.replace(tzinfo=UTC).isoformat() if hasattr(ts, "isoformat") else str(ts),
                tasks=int(cnt or 0),
                success_ratio=float(succ) if succ is not None else None,
                avg_duration_ms=float(avg_dur) if avg_dur is not None else None,
            )
        )
    return {"series": points}


class ActivityItem(BaseModel):
    id: int
    ts: str
    action: str
    path: str
    status_code: int


@router.get("/activity")
def metrics_activity(
    limit: int = Query(default=50, ge=1, le=1000),
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> dict[str, list[ActivityItem]]:
    tenant_id = str(current_user["tenant_id"])
    q = (
        select(
            AuditLog.id,
            AuditLog.timestamp,
            AuditLog.action,
            AuditLog.path,
            AuditLog.status_code,
        )
        .where((AuditLog.tenant_id == tenant_id) | (AuditLog.tenant_id.is_(None)))
        .order_by(AuditLog.id.desc())
        .limit(limit)
    )
    items: list[ActivityItem] = []
    for id_, ts, action, path, status_code in db.execute(q).all():
        items.append(
            ActivityItem(
                id=int(id_),
                ts=ts.replace(tzinfo=UTC).isoformat() if hasattr(ts, "isoformat") else str(ts),
                action=str(action),
                path=str(path),
                status_code=int(status_code),
            )
        )
    return {"items": items}


