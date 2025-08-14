from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.flags.feature_flags import set_flag
from app.core.release.promotion_audit import write_audit
from app.core.release.rollout import (
    current_mode,
    rollback_now,
    set_canary_allowlist,
)
from app.core.telemetry.beta_metrics import BetaMetric, ensure_table_exists
from app.db.session import get_session
from app.api.auth import get_current_user
from ..interconnect import get_interconnect

router = APIRouter(prefix="/admin/beta", tags=["admin-beta"])


class PromoteRequest(BaseModel):
    feature: str = Field(..., min_length=1)
    min_pass_rate: int = Field(ge=0, le=100, default=90)
    allowlist: list[str] = Field(default_factory=list)


def _require_admin(user=Depends(get_current_user)):
    roles = set(user.get("roles", []) if isinstance(user.get("roles", []), list) else [])
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


@router.post("/promote")
def promote(
    payload: PromoteRequest,
    db: Session = Depends(get_session),  # noqa: B008
    user=Depends(_require_admin),  # noqa: B008
) -> dict[str, Any]:
    # Check recent metrics for feature
    ensure_table_exists()
    rows = (
        db.query(BetaMetric)
        .filter(BetaMetric.feature == payload.feature)
        .order_by(desc(BetaMetric.ts))
        .limit(50)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=400, detail="No beta metrics available for feature")

    passed = sum(1 for r in rows if r.status == "pass")
    rate = int((passed * 100) / len(rows))
    if rate < payload.min_pass_rate:
        raise HTTPException(status_code=400, detail=f"Pass rate {rate}% below threshold")

    # Copy flags: enable feature flag for allowlist tenants
    for tid in payload.allowlist:
        set_flag(db, tid, payload.feature, True)

    # Set rollout allowlist
    set_canary_allowlist(payload.allowlist)

    # Audit
    write_audit(db, action="promote", feature=payload.feature, tenant_ids=payload.allowlist, performed_by="admin", details={"pass_rate": rate})
    # Emit deploy.promoted event (best-effort)
    try:
        import asyncio as _asyncio
        async def _emit():
            ic = await get_interconnect()
            await ic.publish(stream="events.ops", type="deploy.promoted", source="admin_promotion", data={"feature": payload.feature, "pass_rate": rate})
        _asyncio.create_task(_emit())
    except Exception:
        pass

    return {"status": "ok", "pass_rate": rate, "mode": current_mode()}


class DemoteRequest(BaseModel):
    feature: str
    tenant_ids: list[str] = Field(default_factory=list)


@router.post("/demote")
def demote(
    payload: DemoteRequest,
    db: Session = Depends(get_session),  # noqa: B008
    user=Depends(_require_admin),  # noqa: B008
) -> dict[str, Any]:
    # Disable flags for tenants
    for tid in payload.tenant_ids:
        set_flag(db, tid, payload.feature, False)

    # Rollback deployment
    rollback_now()

    # Audit
    write_audit(db, action="demote", feature=payload.feature, tenant_ids=payload.tenant_ids, performed_by="admin", details={})
    # Emit deploy.rolled_back event (best-effort)
    try:
        import asyncio as _asyncio
        async def _emit2():
            ic = await get_interconnect()
            await ic.publish(stream="events.ops", type="deploy.rolled_back", source="admin_promotion", data={"feature": payload.feature, "tenants": payload.tenant_ids})
        _asyncio.create_task(_emit2())
    except Exception:
        pass

    return {"status": "ok", "mode": current_mode()}


