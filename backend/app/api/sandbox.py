from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..db.session import get_session
from ..db.models import Employee


router = APIRouter(prefix="/sandbox", tags=["sandbox"])


class SandboxNewIn(BaseModel):
    name: str | None = Field(default=None)
    ttl_minutes: int = Field(default=60, ge=10, le=1440)
    template_key: str | None = Field(default=None, description="Optional marketplace template key")


class SandboxOut(BaseModel):
    employee_id: str
    sandbox_id: str
    expires_at: str


@router.post("/new", response_model=SandboxOut)
def create_sandbox(
    payload: SandboxNewIn,
    db: Session = Depends(get_session),  # noqa: B008
    user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> SandboxOut:
    tenant_id = str(user.get("tenant_id", ""))
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    sandbox_id = str(uuid.uuid4())
    emp_id = f"lab-{sandbox_id[:8]}"
    expires_at = datetime.now(UTC) + timedelta(minutes=payload.ttl_minutes)

    # Minimal lab employee config
    config: dict[str, Any] = {
        "role": {"name": payload.name or "Sandbox Agent", "description": "Ephemeral lab agent"},
        "tools": ["api_caller", "web_scraper"],
        "rag": {"enabled": True, "namespace": f"lab:{sandbox_id}"},
        "lab": True,
        "sandbox_id": sandbox_id,
        "lab_expires_at": expires_at.isoformat(),
    }

    # Create employee row
    emp = Employee(id=emp_id, tenant_id=tenant_id, name=payload.name or emp_id, config=config)
    db.add(emp)
    db.commit()
    return SandboxOut(employee_id=emp.id, sandbox_id=sandbox_id, expires_at=config["lab_expires_at"])



