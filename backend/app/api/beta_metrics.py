from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.telemetry.beta_metrics import BetaMetric, aggregate_metrics, ensure_table_exists
from app.db.session import get_session
from app.api.auth import get_current_user

router = APIRouter(prefix="/metrics", tags=["metrics"])


class MetricIn(BaseModel):
    tenant_id: str
    feature: str
    status: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int | None = None


@router.post("/beta")
def ingest_metric(
    payload: MetricIn,
    db: Session = Depends(get_session),  # noqa: B008
    user=Depends(get_current_user),  # ensure authenticated
) -> dict[str, str]:
    # Enforce tenant-boundary: only allow writing for own tenant
    user_tenant = str(user.get("tenant_id", "")) if isinstance(user, dict) else ""
    if not user_tenant or payload.tenant_id != user_tenant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    ensure_table_exists()
    m = BetaMetric(
        tenant_id=payload.tenant_id,
        feature=payload.feature,
        status=payload.status,
        tokens_in=payload.tokens_in,
        tokens_out=payload.tokens_out,
        latency_ms=payload.latency_ms,
        extra=None,
    )
    db.add(m)
    db.commit()
    return {"status": "ok"}


@router.get("/beta")
def query_metrics(
    tenant_id: str | None = Query(default=None),
    feature: str | None = Query(default=None),
    db: Session = Depends(get_session),  # noqa: B008
    user=Depends(get_current_user),  # ensure authenticated
) -> dict[str, Any]:
    ensure_table_exists()
    # Enforce tenant-boundary on reads as well
    user_tenant = str(user.get("tenant_id", "")) if isinstance(user, dict) else ""
    effective_tenant = tenant_id or user_tenant
    if not effective_tenant:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant_id is required")
    if effective_tenant != user_tenant:
        # Do not allow cross-tenant metric reads
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return aggregate_metrics(db, tenant_id=effective_tenant, feature=feature)


