"""Employee CRUD and execution APIs (tenant-scoped)."""

from __future__ import annotations

from typing import Any
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..core.config import settings
from ..core.employee_builder.employee_builder import EmployeeBuilder
from ..core.runtime.deployment_runtime import DeploymentRuntime
from ..core.logging_config import get_trace_id
from ..core.telemetry.metrics_service import MetricsService
from ..core.security.rate_limit import increment_and_check
from ..db.models import AuditLog, Employee, TaskExecution, Tenant, EmployeeVersion, PerformanceSnapshot
from ..core.quality.guards import idempotency_check_and_store, idempotency_store_response
from ..db.session import engine, get_session
from ..db.models import TaskExecution
from ..core.telemetry.timeline import normalize_events
from ..interconnect import get_interconnect
from ..interconnect.cloudevents import make_event
from ..core.bus import publish as bus_publish

router = APIRouter(prefix="/employees", tags=["employees"])
logger = logging.getLogger(__name__)


class EmployeeIn(BaseModel):
    name: str = Field(..., min_length=1)
    role_name: str
    description: str
    tools: list[str | dict[str, Any]]


class EmployeeOut(BaseModel):
    id: str
    name: str
    tenant_id: str
    owner_user_id: int | None
    config: dict[str, Any]
    active_version_id: int | None = None


class EmployeePerformanceOut(BaseModel):
    success_ratio: float | None
    avg_duration_ms: float | None
    tasks: int
    errors: int
    tool_calls: int


def _require_same_tenant(record_tenant: str, req_tenant: str) -> None:
    if record_tenant != req_tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


class Page(BaseModel):
    items: list[EmployeeOut]
    total: int
    page: int
    page_size: int


@router.get("", response_model=Page)
def list_employees_page(
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
    page: int = Query(default=1, ge=1, le=1000),
    page_size: int = Query(default=20, ge=1, le=1000),
    q: str = Query(default=""),
) -> Page:
    from sqlalchemy import or_
    page_size_clamped = min(int(page_size), 100)
    base = db.query(Employee).filter(Employee.tenant_id == current_user["tenant_id"])
    if q:
        like = f"%{q}%"
        base = base.filter(or_(Employee.name.ilike(like), Employee.id.ilike(like)))
    total = base.count()
    rows = (
        base.order_by(Employee.created_at.desc())
        .offset((int(page) - 1) * page_size_clamped)
        .limit(page_size_clamped)
        .all()
    )
    items = [
        EmployeeOut(
            id=row.id,
            name=row.name,
            tenant_id=row.tenant_id,
            owner_user_id=row.owner_user_id,
            config=row.config,
            active_version_id=row.active_version_id,
        )
        for row in rows
    ]
    return Page(items=items, total=int(total), page=int(page), page_size=int(page_size_clamped))


@router.get("/", response_model=list[EmployeeOut])
def list_employees(
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> list[EmployeeOut]:
    rows = (
        db.query(Employee)
        .filter(Employee.tenant_id == current_user["tenant_id"])
        .order_by(Employee.created_at.desc())
        .all()
    )
    return [
        EmployeeOut(
            id=row.id,
            name=row.name,
            tenant_id=row.tenant_id,
            owner_user_id=row.owner_user_id,
            config=row.config,
            active_version_id=row.active_version_id,
        )
        for row in rows
    ]


@router.post("/", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeIn,
    request: Request,
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> EmployeeOut:
    # Idempotency: dedupe by header key + payload fingerprint
    try:
        import json as _json
        idem_key = request.headers.get("X-Idempotency-Key")
        fp = _json.dumps({"name": payload.name, "role_name": payload.role_name, "description": payload.description, "tools": payload.tools}, sort_keys=True)
        dup, resp_key = idempotency_check_and_store(tenant_id=current_user.get("tenant_id"), key=idem_key, request_fingerprint=fp)
        # If duplicate and we had stored response, return it (best-effort) — not implemented fetch here
        if dup and resp_key is None:
            # Fall through to natural upsert-style behavior (409 on exists)
            pass
    except Exception:
        pass
    # Rate limit employee creation
    try:
        ok = increment_and_check(
            settings.redis_url,
            f"rl:{current_user['tenant_id']}:{current_user['user_id']}:employees:create",
            limit=10,
            window_seconds=60,
        )
    except Exception:
        ok = True
    if not ok:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    try:
        builder = EmployeeBuilder(
            role_name=payload.role_name,
            description=payload.description,
            tools=payload.tools,
        )
        config = builder.build_config()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    # Deterministic ID from name and tenant for demo simplicity
    import hashlib

    eid = hashlib.sha1(f"{current_user['tenant_id']}::{payload.name}".encode()).hexdigest()[
        :16
    ]
    try:
        existing = db.get(Employee, eid)
    except SQLAlchemyError:
        # Ensure required tables exist without creating vector-dependent tables
        try:
            db.rollback()
            from sqlalchemy import inspect

            insp = inspect(engine)
            tables = set(insp.get_table_names())
            if "tenants" not in tables:
                Tenant.__table__.create(bind=engine, checkfirst=True)
            # Create version table before employees to satisfy FK in dev/CI
            try:
                from ..db.models import EmployeeVersion as _EV
                if "employee_versions" not in tables:
                    _EV.__table__.create(bind=engine, checkfirst=True)
            except Exception:
                pass
            if "employees" not in tables:
                Employee.__table__.create(bind=engine, checkfirst=True)
            else:
                # If the table exists but new columns don't, add them best-effort for tests/dev
                try:
                    cols = {c.get("name") for c in insp.get_columns("employees")}
                    if "active_version_id" not in cols:
                        with engine.begin() as conn:
                            conn.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS active_version_id INTEGER"))
                except Exception:
                    pass
        except Exception:
            pass
        existing = db.get(Employee, eid)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee exists")

    # Ensure tenant row exists for FK integrity in minimal test environments
    tenant_id = current_user["tenant_id"]
    try:
        if db.get(Tenant, tenant_id) is None:
            db.add(Tenant(id=tenant_id, name="Default Tenant"))
            db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()

    owner_uid = int(current_user["user_id"]) if str(current_user["user_id"]).isdigit() else None
    row = Employee(
        id=eid,
        tenant_id=tenant_id,
        owner_user_id=owner_uid,
        name=payload.name,
        config=config,
    )
    try:
        db.add(row)
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Create failed") from e
    # Publish interconnect event (best-effort)
    try:
        import asyncio
        trace_id = get_trace_id()
        async def _publish():
            ic = await get_interconnect()
            await ic.publish(
                stream="events.employees",
                type="employee.created",
                source="api.employees",
                subject=row.id,
                tenant_id=row.tenant_id,
                employee_id=row.id,
                trace_id=trace_id,
                actor="api",
                data={"name": row.name},
            )
            await bus_publish({
                "type": "employee.created",
                "tenant_id": row.tenant_id,
                "employee_id": row.id,
                "source": "api",
                "data": {"name": row.name},
            })
        asyncio.create_task(_publish())
    except Exception:
        pass
    out = EmployeeOut(
        id=row.id, name=row.name, tenant_id=row.tenant_id, owner_user_id=row.owner_user_id, config=row.config
    )
    # Store idempotent response for later duplicates (best-effort)
    try:
        idempotency_store_response(tenant_id=current_user.get("tenant_id"), key=request.headers.get("X-Idempotency-Key"), response_payload=out.model_dump())
    except Exception:
        pass
    return out


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: str,
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> EmployeeOut:
    row = db.get(Employee, employee_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_same_tenant(row.tenant_id, current_user["tenant_id"])
    return EmployeeOut(
        id=row.id,
        name=row.name,
        tenant_id=row.tenant_id,
        owner_user_id=row.owner_user_id,
        config=row.config,
        active_version_id=row.active_version_id,
    )


class ExecuteIn(BaseModel):
    task: str
    iterations: int | None = Field(default=1, ge=1, le=10)
    context: dict[str, Any] | None = None


@router.post("/{employee_id}/run")
async def execute_employee(
    employee_id: str,
    payload: ExecuteIn,
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    try:
        ok = increment_and_check(
            settings.redis_url,
            f"rl:{current_user['tenant_id']}:{current_user['user_id']}:employees:{employee_id}:execute",
            limit=120,
            window_seconds=60,
        )
    except Exception:
        ok = True
    if not ok:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    row = db.get(Employee, employee_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_same_tenant(row.tenant_id, current_user["tenant_id"])

    runtime = DeploymentRuntime(employee_config=row.config)
    # Inject tenant/employee into context for downstream metrics
    ctx = dict(payload.context or {})
    ctx.setdefault("tenant_id", current_user["tenant_id"])
    ctx.setdefault("employee_id", row.id)
    # Allow ad-hoc prompt variants via API for experimentation
    # Example: context: { "prompt_variants": ["You are concise.", "Follow chain-of-thought only internally."] }
    results = await runtime.start(payload.task, iterations=payload.iterations or 1, context=ctx)
    # Persist basic execution log
    try:
        for r in results:
            exec_row = TaskExecution(
                tenant_id=row.tenant_id,
                employee_id=row.id,
                user_id=int(current_user["user_id"]),
                task_type=str(r.metadata.get("task_type", "general")),
                prompt=payload.task,
                response=r.output,
                model_used=r.model_used,
                tokens_used=int(r.metadata.get("tokens_used", 0)),
                execution_time=int(r.execution_time * 1000),
                success=bool(r.success),
                error_message=r.error,
                cost_cents=int(r.metadata.get("cost_cents", 0)),
                task_data="",
            )
            db.add(exec_row)
            # Persist metrics rollup per task
            try:
                from ..core.telemetry.metrics_service import TaskMetrics

                MetricsService().rollup_task(
                    db,
                    TaskMetrics(
                        tenant_id=row.tenant_id,
                        employee_id=row.id,
                        duration_ms=int(r.execution_time * 1000),
                        tokens_used=int(r.metadata.get("tokens_used", 0)),
                        success=bool(r.success),
                    ),
                )
            except Exception:
                pass
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    # Attach trace id to response envelope for client correlation
    out = {"results": [r.model_dump() for r in results]}
    trace_id = get_trace_id()
    if trace_id:
        out["trace_id"] = trace_id
    logger.info("Employee run completed")
    # Emit bus event
    try:
        await bus_publish({
            "type": "run.requested",
            "tenant_id": row.tenant_id,
            "employee_id": row.id,
            "user_id": str(current_user.get("user_id")),
            "source": "api",
            "data": {"task": payload.task[:120]},
        })
    except Exception:
        pass
    return out


class TuneRequest(BaseModel):
    # Simple tunables: prompt prefix and tool strategy knobs; runtime will pass into orchestrator
    prompt_prefix: str | None = None
    tool_strategy: dict[str, Any] | None = None
    auto_tune: bool | None = None
    notes: str | None = None


class TuneResponse(BaseModel):
    employee_id: str
    version_id: int
    version: int
    status: str


@router.post("/{employee_id}/tune", response_model=TuneResponse)
def tune_employee(
    employee_id: str,
    payload: TuneRequest,
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> TuneResponse:
    row = db.get(Employee, employee_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_same_tenant(row.tenant_id, current_user["tenant_id"])

    # Create a new version snapshot with merged config
    base_cfg = dict(row.config or {})
    defaults = dict((base_cfg.get("defaults") or {}))
    if payload.prompt_prefix is not None:
        defaults["prompt_prefix"] = payload.prompt_prefix
    if payload.auto_tune is not None:
        defaults["auto_tune"] = bool(payload.auto_tune)
    base_cfg["defaults"] = defaults
    if payload.tool_strategy is not None:
        base_cfg["strategy"] = dict(payload.tool_strategy)

    # Compute next version number
    try:
        EmployeeVersion.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    last = (
        db.query(EmployeeVersion)
        .filter(EmployeeVersion.employee_id == employee_id)
        .order_by(EmployeeVersion.version.desc())
        .first()
    )
    next_version = int((last.version if last else 0) + 1)
    ver = EmployeeVersion(
        employee_id=employee_id,
        version=next_version,
        parent_version_id=(last.id if last else None),
        status="active",
        notes=(payload.notes or ""),
        config=base_cfg,
    )
    db.add(ver)
    db.flush()  # assign id
    # Update employee active_version and config to the new snapshot atomically
    row.config = base_cfg
    row.active_version_id = ver.id
    db.add(row)
    db.commit()
    return TuneResponse(employee_id=employee_id, version_id=int(ver.id), version=next_version, status=ver.status)


class RollbackResponse(BaseModel):
    employee_id: str
    version_id: int
    version: int
    status: str


@router.post("/{employee_id}/rollback/{version}", response_model=RollbackResponse)
def rollback_employee(
    employee_id: str,
    version: int,
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> RollbackResponse:
    row = db.get(Employee, employee_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_same_tenant(row.tenant_id, current_user["tenant_id"])

    ver = (
        db.query(EmployeeVersion)
        .filter(EmployeeVersion.employee_id == employee_id, EmployeeVersion.version == int(version))
        .first()
    )
    if ver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    # Set active version and replace config
    row.config = dict(ver.config or {})
    row.active_version_id = ver.id
    db.add(row)
    db.commit()
    return RollbackResponse(employee_id=employee_id, version_id=int(ver.id), version=int(ver.version), status=str(ver.status))


class SnapshotOut(BaseModel):
    id: int
    employee_id: str
    employee_version_id: int | None
    strategy: str | None
    tasks: int
    successes: int
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    avg_cost_cents: float | None
    created_at: str | None = None


@router.get("/{employee_id}/snapshots", response_model=list[SnapshotOut])
def list_snapshots(
    employee_id: str,
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> list[SnapshotOut]:
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_same_tenant(emp.tenant_id, current_user["tenant_id"])
    try:
        PerformanceSnapshot.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    rows = (
        db.query(PerformanceSnapshot)
        .filter(PerformanceSnapshot.employee_id == employee_id)
        .order_by(PerformanceSnapshot.id.desc())
        .limit(100)
        .all()
    )
    out: list[SnapshotOut] = []
    for r in rows:
        out.append(
            SnapshotOut(
                id=int(r.id),
                employee_id=str(r.employee_id),
                employee_version_id=int(r.employee_version_id) if r.employee_version_id is not None else None,
                strategy=str(r.strategy) if r.strategy else None,
                tasks=int(r.tasks or 0),
                successes=int(r.successes or 0),
                avg_latency_ms=float(r.avg_latency_ms or 0.0) if r.avg_latency_ms is not None else None,
                p95_latency_ms=float(r.p95_latency_ms or 0.0) if r.p95_latency_ms is not None else None,
                avg_cost_cents=float(r.avg_cost_cents or 0.0) if r.avg_cost_cents is not None else None,
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
        )
    return out


class LogOut(BaseModel):
    id: int
    task_type: str
    model_used: str | None
    success: bool
    execution_time: int | None
    error_message: str | None
    created_at: str | None = None


@router.get("/{employee_id}/logs", response_model=list[LogOut])
def get_employee_logs(
    employee_id: str,
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[LogOut]:
    row = db.get(Employee, employee_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_same_tenant(row.tenant_id, current_user["tenant_id"])

    # Query logs; if table missing (dev), return empty list gracefully
    try:
        q = (
            db.query(TaskExecution)
            .filter(
                TaskExecution.tenant_id == row.tenant_id,
                TaskExecution.employee_id == employee_id,
            )
            .order_by(TaskExecution.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    except SQLAlchemyError:
        db.rollback()
        q = []
    out: list[LogOut] = []
    for t in q:
        out.append(
            LogOut(
                id=t.id,
                task_type=t.task_type,
                model_used=t.model_used,
                success=t.success,
                execution_time=t.execution_time,
                error_message=t.error_message,
                created_at=t.created_at.isoformat() if t.created_at else None,
            )
        )
    return out


@router.get("/{employee_id}/timeline")
def get_employee_timeline(
    employee_id: str,
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, object]]:
    # Tenant scoping and normalization
    _require_same_tenant(current_user["tenant_id"], current_user["tenant_id"])  # no-op, kept consistent
    events = normalize_events(
        tenant_id=current_user["tenant_id"], employee_id=employee_id, db=db, limit=limit, offset=offset
    )
    return events


@router.get("/{employee_id}/performance", response_model=EmployeePerformanceOut)
def get_employee_performance(
    employee_id: str,
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> EmployeePerformanceOut:
    from ..core.telemetry.metrics_service import DailyUsageMetric
    row = db.get(Employee, employee_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_same_tenant(row.tenant_id, current_user["tenant_id"])
    try:
        DailyUsageMetric.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    m = (
        db.query(DailyUsageMetric)
        .filter(DailyUsageMetric.tenant_id == row.tenant_id, DailyUsageMetric.employee_id == employee_id)
        .order_by(DailyUsageMetric.day.desc())
        .first()
    )
    if not m:
        return EmployeePerformanceOut(success_ratio=None, avg_duration_ms=None, tasks=0, errors=0, tool_calls=0)
    return EmployeePerformanceOut(success_ratio=float(m.success_ratio or 0.0), avg_duration_ms=float(m.avg_duration_ms or 0.0), tasks=int(m.tasks or 0), errors=int(m.errors or 0), tool_calls=int(m.tool_calls or 0))


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: str,
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> Response:
    row = db.get(Employee, employee_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_same_tenant(row.tenant_id, current_user["tenant_id"])
    # Wrap in transaction; if task_executions table is missing in dev, ignore
    try:
        with db.begin():  # transactional scope
            db.delete(row)
    except Exception:
        db.rollback()
        # Best-effort delete without failing when audit/log tables are absent
        try:
            import asyncio as _asyncio
            async def _emit():
                ic = await get_interconnect()
                await ic.publish(
                    stream="events.employees",
                    type="employee.deleted",
                    source="api.employees",
                    subject=employee_id,
                    tenant_id=row.tenant_id,
                    employee_id=row.id,
                )
            _asyncio.create_task(_emit())
        except Exception:
            pass
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    # Emit deletion on success
    try:
        import asyncio as _asyncio
        async def _emit2():
            ic = await get_interconnect()
            await ic.publish(
                stream="events.employees",
                type="employee.deleted",
                source="api.employees",
                subject=employee_id,
                tenant_id=row.tenant_id,
                employee_id=row.id,
            )
        _asyncio.create_task(_emit2())
    except Exception:
        pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Basic audit logging dependency
async def log_request(
    request: Request,
    response: Response,
    current_user: dict[str, str] | None,
    db: Session,
) -> None:
    try:
        entry = AuditLog(
            tenant_id=(current_user or {}).get("tenant_id"),
            user_id=int((current_user or {}).get("user_id")) if (current_user or {}).get("user_id") else None,
            action="employees_api",
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            meta={"query": dict(request.query_params)},
        )
        db.add(entry)
        db.commit()
    except Exception:  # noqa: BLE001
        # Best-effort audit log
        pass


