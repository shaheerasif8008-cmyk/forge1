from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..db.models import TaskExecution
from ..db.session import get_session

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _require_admin(user: dict[str, Any]) -> None:
    roles = [str(r) for r in (user.get("roles", []) or [])] if isinstance(user, dict) else []
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


@router.get("/active")
def active_employees(
    minutes: int = Query(5, ge=1, le=1440),
    tenant_id: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> dict[str, int]:
    _require_admin(user)
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    q = db.query(TaskExecution.employee_id).filter(TaskExecution.created_at >= cutoff)
    if tenant_id:
        q = q.filter(TaskExecution.tenant_id == tenant_id)
    # Distinct set in Python for cross-dialect simplicity
    active = {row[0] for row in q.all() if row[0] is not None}
    return {"active_employees": len(active)}


