from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_session
from ..db.models import ActionApproval, SupervisorPolicy
from .auth import get_current_user


router = APIRouter(prefix="/hitl", tags=["hitl"])


class ApprovalCreateIn(BaseModel):
    action: str
    payload: dict[str, Any] | None = None


@router.post("/approvals", status_code=status.HTTP_201_CREATED)
def create_approval(payload: ApprovalCreateIn, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    row = ActionApproval(tenant_id=current_user["tenant_id"], employee_id=None, action=payload.action, payload=payload.payload or {}, status="pending")
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status}


@router.get("/approvals")
def list_approvals(current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> list[dict[str, Any]]:  # noqa: B008
    rows = db.query(ActionApproval).filter(ActionApproval.tenant_id == current_user["tenant_id"]).order_by(ActionApproval.created_at.desc()).limit(200).all()
    return [{"id": r.id, "action": r.action, "status": r.status, "created_at": (r.created_at.isoformat() if r.created_at else None)} for r in rows]


class ApprovalDecisionIn(BaseModel):
    decision: str  # approved|rejected
    reason: str | None = None


@router.post("/approvals/{approval_id}/decision")
def decide_approval(approval_id: int, payload: ApprovalDecisionIn, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    row = db.get(ActionApproval, approval_id)
    if not row or row.tenant_id != current_user["tenant_id"]:
        raise HTTPException(status_code=404, detail="approval not found")
    if row.status != "pending":
        raise HTTPException(status_code=400, detail="already decided")
    row.status = "approved" if payload.decision == "approved" else "rejected"
    row.reason = payload.reason
    row.decided_by_user = int(current_user.get("user_id") or 0) if str(current_user.get("user_id") or "").isdigit() else None
    row.decided_at = datetime.now(UTC)
    db.add(row)
    db.commit()
    return {"status": row.status}


@router.post("/supervisor")
def update_supervisor_policy(ghost_mode: bool | None = None, pause_high_impact: bool | None = None, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    tenant_id = current_user["tenant_id"]
    row = db.get(SupervisorPolicy, tenant_id) or SupervisorPolicy(tenant_id=tenant_id)
    if ghost_mode is not None:
        row.ghost_mode = bool(ghost_mode)
    if pause_high_impact is not None:
        row.pause_high_impact = bool(pause_high_impact)
    db.add(row)
    db.commit()
    return {"ghost_mode": row.ghost_mode, "pause_high_impact": row.pause_high_impact}


