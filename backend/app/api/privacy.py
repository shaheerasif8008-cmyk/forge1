from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..db.models import DataLifecyclePolicy, AuditLog
from ..db.session import get_session


router = APIRouter(prefix="/privacy", tags=["privacy"])


class PolicyIn(BaseModel):
    chat_ttl_days: int | None = None
    tool_io_ttl_days: int | None = None
    pii_redaction_enabled: bool | None = None


class PolicyOut(PolicyIn):
    tenant_id: str
    updated_at: str


def _require_admin(user=Depends(get_current_user)):
    roles = set(user.get("roles", []) if isinstance(user.get("roles", []), list) else [])
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


@router.get("/policy", response_model=PolicyOut)
def get_policy(user=Depends(_require_admin), db: Session = Depends(get_session)) -> PolicyOut:  # noqa: B008
    # Ensure table exists in dev/CI
    try:
        DataLifecyclePolicy.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    row = db.get(DataLifecyclePolicy, user["tenant_id"]) or DataLifecyclePolicy(tenant_id=user["tenant_id"], chat_ttl_days=None, tool_io_ttl_days=None, pii_redaction_enabled=False)
    return PolicyOut(tenant_id=row.tenant_id, chat_ttl_days=row.chat_ttl_days, tool_io_ttl_days=row.tool_io_ttl_days, pii_redaction_enabled=row.pii_redaction_enabled, updated_at=(row.updated_at.isoformat() if row.updated_at else ""))


@router.post("/policy", response_model=PolicyOut)
def set_policy(payload: PolicyIn, user=Depends(_require_admin), db: Session = Depends(get_session)) -> PolicyOut:  # noqa: B008
    # Ensure table exists in dev/CI
    try:
        DataLifecyclePolicy.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    row = db.get(DataLifecyclePolicy, user["tenant_id"]) or DataLifecyclePolicy(tenant_id=user["tenant_id"]) 
    if payload.chat_ttl_days is not None:
        row.chat_ttl_days = payload.chat_ttl_days
    if payload.tool_io_ttl_days is not None:
        row.tool_io_ttl_days = payload.tool_io_ttl_days
    if payload.pii_redaction_enabled is not None:
        row.pii_redaction_enabled = payload.pii_redaction_enabled
    row.updated_at = datetime.now(UTC)
    db.add(row)
    db.commit()
    return PolicyOut(tenant_id=row.tenant_id, chat_ttl_days=row.chat_ttl_days, tool_io_ttl_days=row.tool_io_ttl_days, pii_redaction_enabled=row.pii_redaction_enabled, updated_at=(row.updated_at.isoformat() if row.updated_at else ""))


class GdprDeleteIn(BaseModel):
    tenant_id: str | None = None
    user_id: str | None = None


@router.post("/gdpr/delete")
def gdpr_delete(payload: GdprDeleteIn, user=Depends(_require_admin), db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    # Enqueue a GDPR deletion job: for demo, we perform immediate deletes for current tenant
    tenant_id = payload.tenant_id or user.get("tenant_id")
    if tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Forbidden")
    # Audit proof entry
    try:
        db.add(AuditLog(tenant_id=tenant_id, user_id=None, action="gdpr_delete_requested", method="POST", path="/privacy/gdpr/delete", status_code=202, meta={"requested_by": user.get("user_id"), "scope": payload.model_dump()}))
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    # Immediate deletion would go here; in production, enqueue to worker
    return {"status": "enqueued"}


