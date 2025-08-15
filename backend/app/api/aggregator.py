from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_session
from ..db.models import DataConsent, AggregatedSample
from .auth import get_current_user


router = APIRouter(prefix="/aggregator", tags=["aggregator"])


@router.post("/consent")
def set_consent(rag_aggregation: bool | None = None, task_aggregation: bool | None = None, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    row = db.get(DataConsent, current_user["tenant_id"]) or DataConsent(tenant_id=current_user["tenant_id"])
    if rag_aggregation is not None:
        row.rag_aggregation_enabled = bool(rag_aggregation)
    if task_aggregation is not None:
        row.task_aggregation_enabled = bool(task_aggregation)
    db.add(row)
    db.commit()
    return {"rag": row.rag_aggregation_enabled, "task": row.task_aggregation_enabled}


@router.post("/collect")
def collect_sample(sample_type: str, industry: str | None = None, prompt_hash: str | None = None, output_hash: str | None = None, tokens_used: int | None = None, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    consent = db.get(DataConsent, current_user["tenant_id"])
    if not consent:
        raise HTTPException(status_code=403, detail="consent not granted")
    if sample_type == "rag" and not consent.rag_aggregation_enabled:
        raise HTTPException(status_code=403, detail="consent not granted for rag")
    if sample_type == "task" and not consent.task_aggregation_enabled:
        raise HTTPException(status_code=403, detail="consent not granted for task")
    db.add(AggregatedSample(tenant_id=current_user["tenant_id"], industry=industry, sample_type=sample_type, prompt_hash=prompt_hash, output_hash=output_hash, tokens_used=tokens_used, consent_snapshot=True))
    db.commit()
    return {"ok": True}


