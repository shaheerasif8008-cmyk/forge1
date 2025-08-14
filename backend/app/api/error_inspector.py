from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..db.session import get_session
from ..core.telemetry.error_inspector import ErrorSnapshot


router = APIRouter(prefix="/admin/errors", tags=["admin-errors"])


def _require_admin(user=Depends(get_current_user)):
    roles = set(user.get("roles", []) if isinstance(user.get("roles", []), list) else [])
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


@router.get("")
def list_errors(
    limit: int = Query(50, ge=1, le=500),
    user=Depends(_require_admin),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> list[dict[str, Any]]:
    try:
        ErrorSnapshot.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    rows = (
        db.query(ErrorSnapshot)
        .filter(ErrorSnapshot.tenant_id == user.get("tenant_id"))
        .order_by(ErrorSnapshot.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "trace_id": r.trace_id,
            "employee_id": r.employee_id,
            "prompt_preview": r.prompt_preview,
            "error_message": r.error_message,
            "tokens_used": r.tokens_used,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "llm_trace": r.llm_trace,
            "tool_stack": r.tool_stack,
        }
        for r in rows
    ]



