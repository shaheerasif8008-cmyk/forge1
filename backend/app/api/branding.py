from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..api.auth import get_current_user


router = APIRouter(prefix="/branding", tags=["branding"])


class Branding(BaseModel):
    logo_url: str | None = Field(default=None)
    primary_color: str | None = Field(default="#0ea5e9")
    secondary_color: str | None = Field(default="#111827")
    dark_mode: bool = Field(default=True)


_TENANT_BRANDING: dict[str, Branding] = {}


@router.get("")
def get_branding(user: dict[str, Any] = Depends(get_current_user)) -> Branding:  # noqa: B008
    tenant_id = str(user.get("tenant_id", ""))
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return _TENANT_BRANDING.get(tenant_id) or Branding()


@router.post("")
def set_branding(payload: Branding, user: dict[str, Any] = Depends(get_current_user)) -> Branding:  # noqa: B008
    tenant_id = str(user.get("tenant_id", ""))
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    _TENANT_BRANDING[tenant_id] = payload
    return payload



