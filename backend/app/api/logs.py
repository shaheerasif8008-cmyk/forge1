from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..db.models import AuditLog
from ..db.session import get_session

router = APIRouter(prefix="/logs", tags=["logs"])


def _require_admin(user: dict[str, Any]) -> None:
    roles = [str(r) for r in (user.get("roles", []) or [])] if isinstance(user, dict) else []
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


@router.get("")
def get_logs(
    since_hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=50, ge=1, le=1000),
    tenant_id: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> list[dict[str, Any]]:
    _require_admin(user)
    cutoff = datetime.now(UTC) - timedelta(hours=since_hours)

    # Enforce tenant scoping: restrict to caller's tenant
    caller_tenant = str(user.get("tenant_id", ""))
    q = db.query(AuditLog).filter(AuditLog.timestamp >= cutoff, AuditLog.tenant_id == caller_tenant)
    # Return most recent first
    rows = q.order_by(desc(AuditLog.timestamp)).limit(limit).all()

    return [
        {
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "tenant_id": r.tenant_id,
            "user_id": r.user_id,
            "path": r.path,
            "method": r.method,
            "status_code": r.status_code,
        }
        for r in rows
        if r is not None
    ]


