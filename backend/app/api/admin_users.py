from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .auth import get_current_user
from ..db.models import User
from ..db.session import get_session


router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def _require_admin(user: dict[str, Any]) -> None:
    roles = [str(r) for r in (user.get("roles", []) or [])]
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


@router.delete("/{user_id}/erase")
def erase_user(
    user_id: int,
    db: Session = Depends(get_session),  # noqa: B008
    user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, Any]:
    _require_admin(user)
    # Redact basic PII fields as a GDPR stub and schedule deep delete (placeholder)
    row = db.get(User, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        row.email = f"erased_{row.id}@example.invalid"
        row.username = f"user_{row.id}_erased"
        db.add(row)
        db.commit()
        # TODO: enqueue background job to deep-delete related data (sessions, logs, etc.)
    except Exception:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=500, detail="Erase failed")
    return {"status": "scheduled", "user_id": row.id}


