from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..core.telemetry.metrics_service import DailyUsageMetric
from ..db.session import get_session

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _require_admin(user: dict[str, Any]) -> None:
    roles = [str(r) for r in (user.get("roles", []) or [])] if isinstance(user, dict) else []
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


@router.get("")
def get_metrics(
    year: int | None = Query(default=None, ge=2000, le=3000),
    month: int | None = Query(default=None, ge=1, le=12),
    tenant_id: str | None = Query(default=None),
    employee_id: str | None = Query(default=None),
    db: Session = Depends(get_session),  # noqa: B008
    user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, Any]:
    _require_admin(user)

    # Enforce tenant scoping: metrics limited to caller's tenant
    caller_tenant = str(user.get("tenant_id", ""))
    q = db.query(DailyUsageMetric).filter(DailyUsageMetric.tenant_id == caller_tenant)
    # Ignore provided tenant_id if it does not match caller's tenant to avoid leakage
    if employee_id:
        q = q.filter(DailyUsageMetric.employee_id == employee_id)
    if year:
        q = q.filter(extract("year", DailyUsageMetric.day) == year)
    if month:
        q = q.filter(extract("month", DailyUsageMetric.day) == month)

    rows = q.order_by(DailyUsageMetric.day.desc()).limit(1000).all()

    total_tasks = sum(r.tasks for r in rows)
    total_duration_ms = sum(r.total_duration_ms for r in rows)
    total_tokens = sum(r.total_tokens for r in rows)
    total_tool_calls = sum(r.tool_calls for r in rows)
    total_errors = sum(r.errors for r in rows)

    avg_duration_ms = (total_duration_ms / total_tasks) if total_tasks else 0.0
    success_ratio = (
        ((total_tasks - total_errors) / total_tasks) if total_tasks else 0.0
    )

    return {
        "summary": {
            "tasks": total_tasks,
            "avg_duration_ms": avg_duration_ms,
            "tokens": total_tokens,
            "tool_calls": total_tool_calls,
            "errors": total_errors,
            "success_ratio": success_ratio,
        },
        "by_day": [
            {
                "day": r.day.isoformat(),
                "tenant_id": r.tenant_id,
                "employee_id": r.employee_id,
                "tasks": r.tasks,
                "avg_duration_ms": r.avg_duration_ms,
                "tokens": r.total_tokens,
                "tool_calls": r.tool_calls,
                "errors": r.errors,
                "success_ratio": r.success_ratio,
            }
            for r in rows
        ],
    }


@router.get("/prometheus")
def prometheus_metrics(
    user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> Response:
    _require_admin(user)
    # Use default registry export; in-process counters/histograms should be registered globally
    reg = CollectorRegistry()
    output = generate_latest()  # default REGISTRY
    return Response(content=output, media_type=CONTENT_TYPE_LATEST)


