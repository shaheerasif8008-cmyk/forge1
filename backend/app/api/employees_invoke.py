from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.runtime.deployment_runtime import DeploymentRuntime
from ..core.security.employee_keys import authenticate_employee_key
from ..core.security.rate_limit import increment_and_check
from ..core.telemetry.metrics_service import MetricsService, TaskMetrics
from ..core.logging_config import get_trace_id
from ..db.models import Employee, TaskExecution
from ..db.session import get_session
from ..interconnect import get_interconnect


router = APIRouter(prefix="/v1/employees", tags=["employee-invoke"])


class InvokeIn(BaseModel):
    input: str
    context: dict[str, Any] | None = None
    tools: list[str] | None = Field(default=None, description="Optional override tool list")
    stream: bool | None = Field(default=False)


class InvokeOut(BaseModel):
    trace_id: str | None = None
    output: str
    tokens_used: int | None = None
    latency_ms: int
    model_used: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


def _enforce_budgets(
    tenant_id: str, employee_id: str, *, db: Session, max_rps: int | None, daily_cap: int | None
) -> None:
    # Per-employee RPS
    if max_rps and max_rps > 0:
        try:
            ok = increment_and_check(
                settings.redis_url,
                key=f"rl:{tenant_id}:{employee_id}:invoke:rps",
                limit=max_rps,
                window_seconds=1,
            )
        except Exception:
            ok = True
        if not ok:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="RPS limit exceeded")
    # Daily tokens cap checked post-execution when tokens known; we still pre-check calls
    try:
        ok2 = increment_and_check(
            settings.redis_url,
            key=f"rl:{tenant_id}:{employee_id}:invoke:calls:day",
            limit=1000000,
            window_seconds=86400,
        )
    except Exception:
        ok2 = True
    if not ok2:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily call cap exceeded")


@router.post("/{employee_id}/invoke", response_model=InvokeOut)
async def invoke_employee(
    employee_id: str,
    payload: InvokeIn,
    request: Request,
    db: Session = Depends(get_session),  # noqa: B008
) -> InvokeOut:
    # Authenticate via Employee-Key header only
    # Ensure table exists in dev/CI
    try:
        from ..db.models import EmployeeKey

        EmployeeKey.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    principal = authenticate_employee_key(
        request.headers.get("Employee-Key"), db=db, pepper=settings.employee_key_pepper
    )
    if principal is None or principal.employee_id != employee_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    emp = db.get(Employee, employee_id)
    if emp is None or emp.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    conf = emp.config or {}
    daily_tokens_cap = conf.get("daily_tokens_cap")
    rps_limit = conf.get("rps_limit")
    _enforce_budgets(emp.tenant_id, employee_id, db=db, max_rps=rps_limit, daily_cap=daily_tokens_cap)

    runtime = DeploymentRuntime(employee_config=conf)
    ctx = dict(payload.context or {})
    ctx.setdefault("tenant_id", emp.tenant_id)
    ctx.setdefault("employee_id", employee_id)
    if payload.tools:
        ctx["tools"] = payload.tools

    # Emit task.started for employee invoke (best-effort)
    try:
        import asyncio as _asyncio
        async def _emit_start():
            ic = await get_interconnect()
            await ic.publish(
                stream="events.tasks",
                type="task.started",
                source="api.employees_invoke",
                tenant_id=emp.tenant_id,
                employee_id=employee_id,
                data={"input_preview": (payload.input or "")[:120]},
            )
        _asyncio.create_task(_emit_start())
    except Exception:
        pass

    start = time.time()
    results = await runtime.start(payload.input, iterations=1, context=ctx)
    if not results:
        raise HTTPException(status_code=500, detail="No result")
    r = results[-1]
    duration_ms = int((time.time() - start) * 1000)

    # Metrics and persistence
    try:
        exec_row = TaskExecution(
            tenant_id=emp.tenant_id,
            employee_id=emp.id,
            user_id=0,  # external
            task_type=str(r.metadata.get("task_type", "general")),
            prompt=payload.input,
            response=r.output,
            model_used=r.model_used,
            tokens_used=int(r.metadata.get("tokens_used", 0)),
            execution_time=duration_ms,
            success=bool(r.success),
            error_message=r.error,
            task_data="",
        )
        db.add(exec_row)
        MetricsService().rollup_task(
            db,
            TaskMetrics(
                tenant_id=emp.tenant_id,
                employee_id=emp.id,
                duration_ms=duration_ms,
                tokens_used=int(r.metadata.get("tokens_used", 0)),
                success=bool(r.success),
            ),
        )
        db.commit()
    except Exception:
        db.rollback()

    # Daily token budget enforcement post factum
    if isinstance(daily_tokens_cap, int) and daily_tokens_cap >= 0:
        try:
            from redis import Redis

            rds = Redis.from_url(settings.redis_url, decode_responses=True)
            used = rds.incrby(
                f"budgets:{emp.tenant_id}:{emp.id}:tokens:day",
                int(r.metadata.get("tokens_used", 0) or 0),
            )
            rds.expire(f"budgets:{emp.tenant_id}:{emp.id}:tokens:day", 86400, nx=True)
            if used > daily_tokens_cap:
                # Soft exceed: include flag in response; hard exceed: 429
                behavior = str(conf.get("exceed_behavior", "hard")).lower()
                if behavior == "hard":
                    raise HTTPException(status_code=429, detail="Daily token budget exceeded")
        except HTTPException:
            raise
        except Exception:
            pass

    out = InvokeOut(
        trace_id=get_trace_id(),
        output=r.output,
        tokens_used=int(r.metadata.get("tokens_used", 0)) if r.metadata else None,
        latency_ms=duration_ms,
        model_used=r.model_used,
        tool_calls=[t for t in r.metadata.get("tool_calls", [])] if r.metadata and r.metadata.get("tool_calls") else None,
    )
    return out


