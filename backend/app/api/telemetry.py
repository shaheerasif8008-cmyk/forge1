from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..db.models import AuditLog
from ..db.session import get_session


router = APIRouter(prefix="/telemetry", tags=["telemetry"])


class TelemetryIn(BaseModel):
  type: str
  props: dict[str, Any] | None = None


@router.post("")
async def ingest(ev: TelemetryIn, request: Request, user=Depends(get_current_user), db: Session = Depends(get_session)) -> dict[str, str]:  # noqa: B008
    # Store as audit-light record for analytics
    try:
        db.add(AuditLog(tenant_id=user.get("tenant_id"), user_id=int(user.get("user_id")) if str(user.get("user_id", "")).isdigit() else None, action=f"telemetry:{ev.type}", method="POST", path=str(request.url.path), status_code=200, meta=ev.model_dump()))
        db.commit()
    except Exception:
        db.rollback()
    return {"status": "ok"}


