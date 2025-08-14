from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from testing_app.db.session import get_db
from testing_app.models.entities import TestSuite
from testing_app.api.deps import require_service_key


router = APIRouter(prefix="/suites", tags=["suites"])


@router.post("")
def create_suite(payload: dict[str, Any], db: Session = Depends(get_db), _auth=Depends(require_service_key)) -> dict[str, Any]:  # noqa: B008,ARG002
    st = TestSuite(
        name=payload.get("name", "suite"),
        target_env=payload.get("target_env", "staging"),
        scenario_ids=payload.get("scenario_ids"),
        load_profile=payload.get("load_profile"),
        chaos_profile=payload.get("chaos_profile"),
        security_profile=payload.get("security_profile"),
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    return {"id": st.id}


@router.get("")
def list_suites(db: Session = Depends(get_db), _auth=Depends(require_service_key)) -> list[dict[str, Any]]:  # noqa: B008,ARG002
    rows = db.query(TestSuite).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "target_env": getattr(r.target_env, "value", str(r.target_env)),
            "has_load": bool(r.load_profile),
            "has_chaos": bool(r.chaos_profile),
            "has_security": bool(r.security_profile),
        }
        for r in rows
    ]


