from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from testing_app.db.session import get_db
from testing_app.models.entities import TestScenario
from testing_app.api.deps import require_service_key


router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.post("")
def create_scenario(payload: dict[str, Any], db: Session = Depends(get_db), _auth=Depends(require_service_key)) -> dict[str, Any]:  # noqa: B008,ARG002
    sc = TestScenario(
        kind=payload.get("kind", "integration"),
        name=payload.get("name", "unnamed"),
        description=payload.get("description"),
        inputs=payload.get("inputs"),
        asserts=payload.get("asserts"),
        tags=payload.get("tags"),
        disabled=1 if payload.get("disabled") else 0,
    )
    db.add(sc)
    db.commit()
    db.refresh(sc)
    return {"id": sc.id}


@router.get("")
def list_scenarios(db: Session = Depends(get_db), _auth=Depends(require_service_key)) -> list[dict[str, Any]]:  # noqa: B008,ARG002
    rows = db.query(TestScenario).all()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "kind": getattr(r.kind, "value", str(r.kind)),
                "name": r.name,
                "tags": r.tags or [],
                "disabled": bool(r.disabled),
            }
        )
    return out


