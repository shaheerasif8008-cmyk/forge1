from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import extract
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..core.telemetry.metrics_service import DailyUsageMetric
from ..db.session import get_session


router = APIRouter(prefix="/client/metrics", tags=["metrics-client"])


@router.get("/summary")
def summary(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_session),  # noqa: B008
    user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, Any]:
    tenant_id = str(user.get("tenant_id", ""))
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    since_day = (datetime.now(UTC) - timedelta(hours=hours)).date()
    rows = (
        db.query(DailyUsageMetric)
        .filter(
            DailyUsageMetric.tenant_id == tenant_id,
            DailyUsageMetric.day >= since_day,
        )
        .order_by(DailyUsageMetric.day.desc())
        .limit(1000)
        .all()
    )

    total_tasks = sum(r.tasks for r in rows)
    total_duration_ms = sum(r.total_duration_ms for r in rows)
    total_tokens = sum(r.total_tokens for r in rows)
    total_errors = sum(r.errors for r in rows)

    avg_duration_ms = (total_duration_ms / total_tasks) if total_tasks else 0.0
    success_ratio = (
        ((total_tasks - total_errors) / total_tasks) if total_tasks else 0.0
    )
    # naive cost estimate: $2 per 1M tokens → cents per token = 0.0002; adjust per model later
    cost_cents = round(total_tokens * 0.0002, 2)

    return {
        "tasks": total_tasks,
        "avg_duration_ms": avg_duration_ms,
        "success_ratio": success_ratio,
        "tokens": total_tokens,
        "cost_cents": cost_cents,
        "by_day": [
            {
                "day": r.day.isoformat(),
                "tasks": r.tasks,
                "avg_duration_ms": r.avg_duration_ms,
                "success_ratio": r.success_ratio,
                "tokens": r.total_tokens,
                "errors": r.errors,
            }
            for r in rows
        ],
    }


@router.get("/active")
def active_employees(
    minutes: int = Query(5, ge=1, le=1440),
    db: Session = Depends(get_session),  # noqa: B008
    user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, int]:
    from datetime import datetime, UTC, timedelta
    from ..db.models import TaskExecution

    tenant_id = str(user.get("tenant_id", ""))
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    q = (
        db.query(TaskExecution.employee_id)
        .filter(TaskExecution.created_at >= cutoff)
        .filter(TaskExecution.tenant_id == tenant_id)
    )
    active = {row[0] for row in q.all() if row[0] is not None}
    return {"active_employees": len(active)}



