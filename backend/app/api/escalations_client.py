from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..db.models import Escalation
from ..db.session import get_session


router = APIRouter(prefix="/client/escalations", tags=["escalations-client"])


class EscalationIn(BaseModel):
  reason: str = Field(..., min_length=3, max_length=500)
  employee_id: str | None = None


class EscalationOut(BaseModel):
  id: int
  status: str


@router.post("", response_model=EscalationOut)
def create_escalation(
  payload: EscalationIn,
  db: Session = Depends(get_session),  # noqa: B008
  user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> EscalationOut:
  tenant_id = str(user.get("tenant_id", ""))
  if not tenant_id:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
  # Ensure table exists in dev/test
  try:
    Escalation.__table__.create(bind=db.get_bind(), checkfirst=True)
  except Exception:
    pass
  row = Escalation(
    tenant_id=tenant_id,
    employee_id=payload.employee_id,
    user_id=int(user.get("user_id")) if str(user.get("user_id", "")).isdigit() else None,
    reason=payload.reason.strip()[:500],
    status="open",
  )
  db.add(row)
  db.commit()
  return EscalationOut(id=int(row.id), status=row.status)



