from __future__ import annotations

import os
import secrets
from typing import Any
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..db.models import Employee, EmployeeKey
from ..db.session import get_session
from ..core.config import settings
from ..core.security.employee_keys import generate_key_pair
from uuid import uuid4

router = APIRouter(prefix="/admin/keys", tags=["admin-keys"])
router_admin_employees = APIRouter(prefix="/admin/employees", tags=["admin-keys"])


def require_admin(user=Depends(get_current_user)):
    roles = set(user.get("roles", []) if isinstance(user.get("roles", []), list) else [])
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


def _redis():
    try:
        from redis import Redis

        from ..core.config import settings

        return Redis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        return None


@router.get("/employees")
def list_employee_usage(
    tenant_id: str = Query(...),
    db: Session = Depends(get_session),  # noqa: B008
    user: dict[str, Any] = Depends(require_admin),  # noqa: B008
) -> list[dict[str, Any]]:
    # Enforce tenant scoping: admins can only view their own tenant
    if tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    # List employees for tenant with usage from Redis counters
    emps = (
        db.query(Employee)
        .filter(Employee.tenant_id == tenant_id)
        .order_by(Employee.created_at.desc())
        .all()
    )
    r = _redis()
    out: list[dict[str, Any]] = []
    for e in emps:
        tokens = tasks = errors = 0
        if r is not None:
            try:
                tokens = int(r.get(f"metrics:employee:{e.id}:tokens") or 0)
                tasks = int(r.get(f"metrics:employee:{e.id}:tasks") or 0)
                errors = int(r.get(f"metrics:employee:{e.id}:errors") or 0)
            except Exception:
                pass
        conf = e.config or {}
        out.append(
            {
                "employee_id": e.id,
                "name": e.name,
                "tokens_today": tokens,
                "tasks_today": tasks,
                "errors_today": errors,
                "daily_tokens_cap": conf.get("daily_tokens_cap"),
                "rps_limit": conf.get("rps_limit"),
                "exceed_behavior": conf.get("exceed_behavior", "hard"),
                "api_key_set": bool(conf.get("api_key")),
            }
        )
    return out


class KeyCreateResponse(BaseModel):
    prefix: str
    secret_once: str
    key_id: str


def _create_employee_key_impl(
    employee_id: str,
    db: Session = Depends(get_session),  # noqa: B008
    user: dict[str, Any] = Depends(require_admin),  # noqa: B008
) -> KeyCreateResponse:
    e = db.get(Employee, employee_id)
    if e is None or e.tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=404, detail="Not found")
    # Ensure table exists for dev/test environments without full migrations
    try:
        EmployeeKey.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    prefix, secret_once, hashed = generate_key_pair(pepper=settings.employee_key_pepper)
    key_row = EmployeeKey(
        id=str(uuid4()),
        tenant_id=e.tenant_id,
        employee_id=e.id,
        prefix=prefix,
        hashed_secret=hashed,
        status="active",
        scopes={},
        expires_at=None,
    )
    db.add(key_row)
    db.commit()
    return KeyCreateResponse(prefix=prefix, secret_once=secret_once, key_id=key_row.id)


@router.post("/employees/{employee_id}/keys", response_model=KeyCreateResponse)
def create_employee_key(
    employee_id: str,
    db: Session = Depends(get_session),  # noqa: B008
    user: dict[str, Any] = Depends(require_admin),  # noqa: B008
) -> KeyCreateResponse:
    return _create_employee_key_impl(employee_id, db, user)  # type: ignore[arg-type]


@router_admin_employees.post("/{employee_id}/keys", response_model=KeyCreateResponse)
def create_employee_key_alt(
    employee_id: str,
    db: Session = Depends(get_session),  # noqa: B008
    user: dict[str, Any] = Depends(require_admin),  # noqa: B008
) -> KeyCreateResponse:
    return _create_employee_key_impl(employee_id, db, user)  # type: ignore[arg-type]


class QuotaIn(BaseModel):
    daily_tokens_cap: int | None = Field(default=None, ge=0)
    rps_limit: int | None = Field(default=None, ge=0)
    exceed_behavior: str | None = Field(default=None)


@router.patch("/employee/{employee_id}/quota")
def update_quota(
    employee_id: str,
    payload: QuotaIn,
    db: Session = Depends(get_session),  # noqa: B008
    user: dict[str, Any] = Depends(require_admin),  # noqa: B008
) -> dict[str, str]:
    e = db.get(Employee, employee_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Not found")
    if e.tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=404, detail="Not found")
    conf = dict(e.config or {})
    for k in ("daily_tokens_cap", "rps_limit", "exceed_behavior"):
        if k in payload:
            conf[k] = payload[k]
    e.config = conf
    db.add(e)
    db.commit()
    return {"status": "ok"}


# Back-compat: rotate per-employee inline API key stored in Employee.config
# Maintains existing tests and UI flows. New EaaS keys live in employee_keys table.
@router.post("/employee/{employee_id}/rotate")
def rotate_employee_key_legacy(
    employee_id: str,
    db: Session = Depends(get_session),  # noqa: B008
    user: dict[str, Any] = Depends(require_admin),  # noqa: B008
) -> dict[str, str]:
    e = db.get(Employee, employee_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Not found")
    if e.tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=404, detail="Not found")
    cfg = dict(e.config or {})
    cfg["api_key"] = secrets.token_hex(16)
    cfg["api_key_revoked"] = False
    e.config = cfg
    db.add(e)
    db.commit()
    return {"status": "ok"}


class KeyActionResponse(BaseModel):
    key_id: str
    status: str


@router.post("/{key_id}/revoke", response_model=KeyActionResponse)
def revoke_key(
    key_id: str,
    db: Session = Depends(get_session),  # noqa: B008
    user: dict[str, Any] = Depends(require_admin),  # noqa: B008
) -> KeyActionResponse:
    row: EmployeeKey | None = db.get(EmployeeKey, key_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    # Verify tenant ownership via employee
    emp = db.get(Employee, row.employee_id)
    if emp is None or emp.tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=404, detail="Not found")
    row.status = "revoked"
    db.add(row)
    db.commit()
    return KeyActionResponse(key_id=row.id, status=row.status)


@router.post("/{key_id}/rotate", response_model=KeyCreateResponse)
def rotate_key(
    key_id: str,
    db: Session = Depends(get_session),  # noqa: B008
    user: dict[str, Any] = Depends(require_admin),  # noqa: B008
) -> KeyCreateResponse:
    row: EmployeeKey | None = db.get(EmployeeKey, key_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    emp = db.get(Employee, row.employee_id)
    if emp is None or emp.tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=404, detail="Not found")
    # Revoke old and create new secret for same employee
    row.status = "revoked"
    db.add(row)
    prefix, secret_once, hashed = generate_key_pair(pepper=settings.employee_key_pepper)
    new_row = EmployeeKey(
        id=str(uuid4()),
        tenant_id=emp.tenant_id,
        employee_id=emp.id,
        prefix=prefix,
        hashed_secret=hashed,
        status="active",
        scopes=row.scopes or {},
        expires_at=None,
    )
    db.add(new_row)
    db.commit()
    return KeyCreateResponse(prefix=prefix, secret_once=secret_once, key_id=new_row.id)


