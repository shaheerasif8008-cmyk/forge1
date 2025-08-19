from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..db.models import Employee, Escalation, TaskExecution
from ..db.session import get_session
from ..core.runtime.deployment_runtime import DeploymentRuntime

router = APIRouter(prefix="/admin/escalations", tags=["admin-escalations"])


def require_admin(user=Depends(get_current_user)):
    roles = set(user.get("roles", []) if isinstance(user.get("roles", []), list) else [])
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


@router.get("/")
def list_escalations(
    tenant_id: str = Query(...),
    status_filter: str | None = Query(default=None),
    db: Session = Depends(get_session),  # noqa: B008
    user=Depends(require_admin),  # noqa: B008
) -> list[dict[str, Any]]:
    # Enforce tenant scoping for admin views
    if tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    q = db.query(Escalation).filter(Escalation.tenant_id == tenant_id)
    if status_filter:
        q = q.filter(Escalation.status == status_filter)
    rows = q.order_by(Escalation.id.desc()).limit(100).all()
    # join employee names
    out: list[dict[str, Any]] = []
    for e in rows:
        name = None
        if e.employee_id:
            emp = db.get(Employee, e.employee_id)
            name = emp.name if emp else None
        out.append(
            {
                "id": e.id,
                "employee_id": e.employee_id,
                "employee_name": name,
                "reason": e.reason,
                "status": e.status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
        )
    return out


@router.post("/{escalation_id}/approve")
def approve_escalation(
    escalation_id: int,
    db: Session = Depends(get_session),  # noqa: B008
    user=Depends(require_admin),  # noqa: B008
) -> dict[str, str]:
    e = db.get(Escalation, escalation_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Not found")
    if e.tenant_id and e.tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=404, detail="Not found")
    e.status = "approved"
    db.add(e)
    db.commit()
    return {"status": "ok"}


@router.post("/{escalation_id}/reject")
def reject_escalation(
    escalation_id: int,
    db: Session = Depends(get_session),  # noqa: B008
    user=Depends(require_admin),  # noqa: B008
) -> dict[str, str]:
    e = db.get(Escalation, escalation_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Not found")
    if e.tenant_id and e.tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=404, detail="Not found")
    e.status = "rejected"
    db.add(e)
    db.commit()
    return {"status": "ok"}


@router.post("/{escalation_id}/retry")
async def retry_escalation(
    escalation_id: int,
    payload: dict[str, Any] | None = None,
    db: Session = Depends(get_session),  # noqa: B008
    user=Depends(require_admin),  # noqa: B008
) -> dict[str, Any]:
    e = db.get(Escalation, escalation_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Not found")
    if not e.employee_id:
        raise HTTPException(status_code=400, detail="Missing employee_id on escalation")
    if e.tenant_id and e.tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=404, detail="Not found")

    emp = db.get(Employee, e.employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Find last task execution prompt for the employee
    last_exec = (
        db.query(TaskExecution)
        .filter(TaskExecution.employee_id == emp.id)
        .order_by(TaskExecution.id.desc())
        .first()
    )
    prompt = (last_exec.prompt if last_exec and last_exec.prompt else None) or (
        (payload or {}).get("prompt_override") if isinstance(payload, dict) else None
    )
    if not prompt:
        raise HTTPException(status_code=400, detail="No prompt available; provide prompt_override")

    try:
        runtime = DeploymentRuntime(employee_config=emp.config)
        results = await runtime.start(seed_task=prompt, iterations=1, context={})
        success = bool(results and getattr(results[0], "success", False))
        if success:
            e.status = "resolved"
            db.add(e)
            db.commit()
        return {"status": "ok", "success": success}
    except Exception as exc:  # noqa: BLE001
        # Return gracefully with success False so callers can surface error and keep UI responsive
        return {"status": "ok", "success": False, "error": str(exc)}


