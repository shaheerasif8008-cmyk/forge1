from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.flags.feature_flags import FeatureFlag, set_flag
from app.db.session import get_session
from app.api.auth import get_current_user

router = APIRouter(prefix="/admin/flags", tags=["admin-flags"])


class FlagSetRequest(BaseModel):
    tenant_id: str
    flag: str
    enabled: bool


def require_admin(user=Depends(get_current_user)):
    roles = set(user.get("roles", []) if isinstance(user.get("roles", []), list) else [])
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


@router.get("/list", dependencies=[Depends(require_admin)])
def list_flags(tenant_id: str, db: Session = Depends(get_session)) -> list[dict]:
    rows = db.query(FeatureFlag).filter(FeatureFlag.tenant_id == tenant_id).order_by(FeatureFlag.flag).all()
    return [
        {"tenant_id": r.tenant_id, "flag": r.flag, "enabled": r.enabled, "updated_at": r.updated_at}
        for r in rows
    ]


@router.post("/set", dependencies=[Depends(require_admin)])
def set_flag_endpoint(payload: FlagSetRequest, db: Session = Depends(get_session)) -> dict:
    # Best-effort rate limit and audit is handled by app middleware; keep endpoint minimal
    set_flag(db, payload.tenant_id, payload.flag, payload.enabled)
    return {"status": "ok"}


