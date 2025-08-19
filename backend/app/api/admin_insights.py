from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .auth import get_current_user
from ..db.session import get_session
from ..db.models import AiInsight


router = APIRouter(prefix="/admin/insights", tags=["admin-insights"])


def _require_admin(user: dict[str, Any]) -> None:
    roles = [str(r) for r in (user.get("roles", []) or [])]
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


@router.get("")
def list_insights(
    db: Session = Depends(get_session),  # noqa: B008
    user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[dict[str, Any]]:
    _require_admin(user)
    # Ensure table exists in dev/CI
    try:
        # Table managed by Alembic
        pass
    except Exception:
        pass
    rows = db.query(AiInsight).order_by(AiInsight.id.desc()).limit(100).all()
    return [
        {
            "id": r.id,
            "actor": r.actor,
            "title": r.title,
            "body": r.body,
            "labels": r.labels or {},
            "metrics": r.metrics or {},
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


