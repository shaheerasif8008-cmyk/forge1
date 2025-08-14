from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from pydantic import BaseModel, Field

from app.core.release.rollout import (
    current_mode as rollout_current_mode,
)
from app.core.release.rollout import (
    rollback_now as rollout_rollback_now,
)
from app.core.release.rollout import (
    set_canary_allowlist as rollout_set_allowlist,
)
from app.core.release.rollout import (
    set_canary_percent as rollout_set_percent,
)
from app.api.auth import get_current_user

router = APIRouter(prefix="/admin/release", tags=["admin-release"])


def require_admin(user=Depends(get_current_user)):
    roles = set(user.get("roles", []) if isinstance(user.get("roles", []), list) else [])
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


class PercentIn(BaseModel):
    percent: int = Field(ge=0, le=100)


class AllowlistIn(BaseModel):
    tenant_ids: list[str]


@router.get("/mode")
def current_mode(user=Depends(require_admin)) -> dict:
    # Tenant-scoped view; current rollout mode is global but access is tenant-admin only
    return rollout_current_mode()


@router.post("/percent")
def set_percent(payload: PercentIn, user=Depends(require_admin)) -> dict[str, Literal["ok"]]:
    rollout_set_percent(payload.percent)
    return {"status": "ok"}


@router.post("/allowlist")
def set_allowlist(payload: AllowlistIn, user=Depends(require_admin)) -> dict[str, Literal["ok"]]:
    # Force allowlist to caller's tenant only to preserve isolation
    rollout_set_allowlist([user.get("tenant_id")])
    return {"status": "ok"}


@router.post("/rollback")
def rollback(user=Depends(require_admin)) -> dict[str, Literal["ok"]]:
    rollout_rollback_now()
    return {"status": "ok"}


