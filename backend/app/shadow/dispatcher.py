from __future__ import annotations

import random
import uuid
from typing import Any

from sqlalchemy.orm import Session

from ..db.models import CanaryConfig, ShadowInvocation


def should_shadow(db: Session, *, tenant_id: str, employee_id: str) -> tuple[bool, CanaryConfig | None]:
    # Table managed by Alembic
    cfg = (
        db.query(CanaryConfig)
        .filter(CanaryConfig.tenant_id == tenant_id, CanaryConfig.employee_id == employee_id)
        .one_or_none()
    )
    if cfg and cfg.status in {"active"} and int(cfg.percent or 0) > 0:
        return (random.randint(1, 100) <= int(cfg.percent), cfg)
    return (False, cfg)


def tee_and_record(db: Session, *, tenant_id: str, employee_id: str, shadow_employee_id: str, input_text: str, primary_output: str | None, shadow_output: str | None, score: float | None) -> str:
    # Table managed by Alembic
    corr = uuid.uuid4().hex[:16]
    row = ShadowInvocation(
        tenant_id=tenant_id,
        employee_id=employee_id,
        shadow_employee_id=shadow_employee_id,
        correlation_id=corr,
        input=input_text,
        primary_output=primary_output,
        shadow_output=shadow_output,
        score=score,
    )
    db.add(row)
    db.commit()
    return corr


