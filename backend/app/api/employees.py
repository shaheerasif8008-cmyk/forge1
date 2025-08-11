"""Employee CRUD and execution APIs (tenant-scoped)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..api.auth import get_current_user
from ..core.employee_builder.employee_builder import EmployeeBuilder
from ..core.runtime.deployment_runtime import DeploymentRuntime
from ..db.models import AuditLog, Employee, TaskExecution, Tenant
from ..core.security.rate_limit import increment_and_check
from ..core.config import settings
from ..db.session import get_session, engine


router = APIRouter(prefix="/employees", tags=["employees"])


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


def _require_same_tenant(record_tenant: str, req_tenant: str) -> None:
    if record_tenant != req_tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


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
        )
        for row in rows
    ]


@router.post("/", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeIn,
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> EmployeeOut:
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
    builder = EmployeeBuilder(
        role_name=payload.role_name,
        description=payload.description,
        tools=payload.tools,
    )
    config = builder.build_config()

    # Deterministic ID from name and tenant for demo simplicity
    import hashlib

    eid = hashlib.sha1(f"{current_user['tenant_id']}::{payload.name}".encode("utf-8")).hexdigest()[
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
            if "employees" not in tables:
                Employee.__table__.create(bind=engine, checkfirst=True)
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

    row = Employee(
        id=eid,
        tenant_id=tenant_id,
        owner_user_id=int(current_user["user_id"]),
        name=payload.name,
        config=config,
    )
    db.add(row)
    db.commit()
    return EmployeeOut(
        id=row.id, name=row.name, tenant_id=row.tenant_id, owner_user_id=row.owner_user_id, config=row.config
    )


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
        id=row.id, name=row.name, tenant_id=row.tenant_id, owner_user_id=row.owner_user_id, config=row.config
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
    results = await runtime.start(
        payload.task, iterations=payload.iterations or 1, context=payload.context or {}
    )
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
                task_data="",
            )
            db.add(exec_row)
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    return {"results": [r.model_dump() for r in results]}


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
    db.delete(row)
    db.commit()
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


