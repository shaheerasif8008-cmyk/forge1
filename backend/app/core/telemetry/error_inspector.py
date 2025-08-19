from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from ...db.models import Base


class ErrorSnapshot(Base):
    __tablename__ = "error_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), index=True, nullable=True)
    employee_id = Column(String(100), index=True, nullable=True)
    trace_id = Column(String(64), index=True, nullable=True)
    task_type = Column(String(50), nullable=True)
    prompt_preview = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    tool_stack = Column(JSONB, nullable=True)
    llm_trace = Column(JSONB, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


def capture_error_snapshot(
    db: Session,
    *,
    tenant_id: str | None,
    employee_id: str | None,
    trace_id: str | None,
    task_type: str | None,
    prompt: str | None,
    error_message: str | None,
    tool_stack: list[dict[str, Any]] | None,
    llm_trace: dict[str, Any] | None,
    tokens_used: int | None,
) -> None:
    """Persist a redacted snapshot for Error Inspector.

    The caller should ensure prompt is redacted of secrets; we only store a short preview here.
    """

    try:
        row = ErrorSnapshot(
            tenant_id=tenant_id,
            employee_id=employee_id,
            trace_id=trace_id,
            task_type=task_type,
            prompt_preview=(prompt or "")[:200],
            error_message=str(error_message or "")[:1000],
            tool_stack=tool_stack or [],
            llm_trace=llm_trace or {},
            tokens_used=int(tokens_used or 0),
        )
        db.add(row)
        db.commit()
    except Exception:
        db.rollback()



