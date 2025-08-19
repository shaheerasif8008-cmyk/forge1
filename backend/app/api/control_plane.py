from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
import os
import httpx
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..db.models import CanaryConfig
from ..db.session import get_session


router = APIRouter(prefix="/control", tags=["control-plane"])


def require_admin(user=Depends(get_current_user)):
    roles = set(user.get("roles", []) if isinstance(user.get("roles", []), list) else [])
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


class CanaryIn(BaseModel):
    percent: int = Field(ge=0, le=100)
    threshold: float = Field(ge=0.0, le=1.0)
    windows: int = Field(ge=1, le=1000)
    shadow_employee_id: str | None = None


@router.post("/employee/{employee_id}/canary")
def set_canary(employee_id: str, payload: CanaryIn, db: Session = Depends(get_session), user=Depends(require_admin)) -> dict[str, Any]:  # noqa: B008
    tenant_id = str(user.get("tenant_id", ""))
    # Table managed by Alembic
    cfg = (
        db.query(CanaryConfig)
        .filter(CanaryConfig.tenant_id == tenant_id, CanaryConfig.employee_id == employee_id)
        .one_or_none()
    )
    if cfg is None:
        cfg = CanaryConfig(
            tenant_id=tenant_id,
            employee_id=employee_id,
            shadow_employee_id=payload.shadow_employee_id or employee_id,
            percent=int(payload.percent),
            threshold=float(payload.threshold),
            windows=int(payload.windows),
            status="active" if payload.percent > 0 else "off",
        )
        db.add(cfg)
    else:
        cfg.shadow_employee_id = payload.shadow_employee_id or cfg.shadow_employee_id
        cfg.percent = int(payload.percent)
        cfg.threshold = float(payload.threshold)
        cfg.windows = int(payload.windows)
        cfg.status = "active" if payload.percent > 0 else "off"
        db.add(cfg)
    db.commit()
    return {"status": "ok", "config": {"percent": cfg.percent, "threshold": cfg.threshold, "windows": cfg.windows}}


@router.post("/testpack/run")
def run_testpack(suite_name: str = "Functional-Core", target_api_url: str | None = None, user=Depends(require_admin)) -> dict[str, Any]:  # noqa: B008
    # Forward to Testing App and return run_id
    testing_url = os.getenv("TESTING_APP_URL", "http://localhost:8002")
    api = f"{testing_url.rstrip('/')}/api/v1"
    key = os.getenv("TESTING_SERVICE_KEY", "")
    # Look up suite id by name
    with httpx.Client(timeout=15.0) as client:
        r = client.get(f"{api}/suites", headers={"X-Testing-Service-Key": key})
        r.raise_for_status()
        suites = r.json()
        sid = None
        for s in suites:
            if str(s.get("name", "")) == suite_name:
                sid = s.get("id")
                break
        if sid is None:
            raise HTTPException(status_code=404, detail="suite not found")
        rr = client.post(
            f"{api}/runs",
            headers={"X-Testing-Service-Key": key, "Content-Type": "application/json"},
            json={"suite_id": sid, "target_api_url": target_api_url},
        )
        rr.raise_for_status()
        return rr.json()

