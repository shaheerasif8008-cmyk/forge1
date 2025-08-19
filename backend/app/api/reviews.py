from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..db.session import get_session
from ..db.models import TaskExecution, TraceSpan
from ..api.auth import get_current_user


router = APIRouter(prefix="/reviews", tags=["reviews"])


class ToolCall(BaseModel):
    name: str
    duration_ms: int | None = None
    status: str | None = None
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None


class TaskTrace(BaseModel):
    task_id: int
    model_used: str | None
    success: bool
    execution_time: int | None
    tool_calls: list[ToolCall]


@router.get("/{task_id}", response_model=TaskTrace)
def get_task_review(task_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> TaskTrace:  # noqa: B008
    row = db.get(TaskExecution, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="not found")
    if row.tenant_id != current_user.get("tenant_id"):
        raise HTTPException(status_code=404, detail="not found")
    # Find trace spans for this task by correlating recent spans with same employee + nearest time
    # Prefer spans of type 'tool' under the same tenant/employee and near creation time
    # Narrow query by time window around the task to avoid scanning too many spans (reduce N+1-like behavior)
    window_start = (row.created_at or row.updated_at) if hasattr(row, "created_at") else None
    q = db.query(TraceSpan).filter(
        and_(TraceSpan.tenant_id == row.tenant_id, TraceSpan.employee_id == row.employee_id)
    )
    if window_start is not None:
        try:
            from datetime import timedelta

            q = q.filter(TraceSpan.started_at >= window_start - timedelta(minutes=10))
        except Exception:
            pass
    spans = q.order_by(TraceSpan.started_at.desc()).limit(200).all()
    tool_calls: list[ToolCall] = []
    for s in spans:
        if (s.span_type or "").lower() == "tool":
            inp = s.input or {}
            out = s.output or {}
            # Redact prompt/credentials if present
            if "prompt" in inp:
                inp["prompt"] = "***redacted***"
            tool_calls.append(
                ToolCall(
                    name=s.name,
                    duration_ms=int(s.duration_ms or 0),
                    status=s.status,
                    input=inp,
                    output=out,
                )
            )
    return TaskTrace(
        task_id=int(row.id),
        model_used=row.model_used,
        success=bool(row.success),
        execution_time=int(row.execution_time or 0),
        tool_calls=tool_calls,
    )


