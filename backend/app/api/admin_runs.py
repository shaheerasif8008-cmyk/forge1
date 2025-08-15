from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..db.models import RunFailure, Employee, AuditLog
from ..db.session import get_session
from ..core.config import settings

try:
    import redis.asyncio as redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore


router = APIRouter(prefix="/admin/runs", tags=["admin-runs"])


def _require_admin(user=Depends(get_current_user)):
    roles = set(user.get("roles", []) if isinstance(user.get("roles", []), list) else [])
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


class ReplayIn(BaseModel):
    reason: str | None = None
    policy_override: dict[str, Any] | None = None


@router.post("/{failure_id}/replay")
async def replay_run(failure_id: int, payload: ReplayIn, user=Depends(_require_admin), db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    row: RunFailure | None = db.get(RunFailure, failure_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    # enqueue to Redis DLQ stream for workers to pick up
    if redis is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    client = redis.from_url(settings.redis_url, decode_responses=True)  # type: ignore
    msg = {
        "type": "run.replay",
        "tenant_id": row.tenant_id,
        "employee_id": row.employee_id,
        "reason": payload.reason or row.reason or "",
        "policy_override": payload.policy_override or {},
        "payload": row.payload or {},
    }
    msg_id = await client.xadd("runs-dlq", {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in msg.items()})
    # audit
    try:
        db.add(AuditLog(tenant_id=row.tenant_id, user_id=int(user.get("user_id")) if str(user.get("user_id", "")).isdigit() else None, action="run.replay", method="POST", path=f"/admin/runs/{failure_id}/replay", status_code=202, meta={"msg_id": msg_id}))
        row.status = "queued"
        db.add(row)
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    return {"status": "queued", "msg_id": msg_id}


