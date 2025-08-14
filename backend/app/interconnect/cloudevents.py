"""CloudEvents v1.0 envelope and helpers for internal event bus.

Spec-compliant minimal schema with a few extension attributes we standardize on:
- tenant_id: str | None
- employee_id: str | None
- trace_id: str | None
- actor: str | None  (originating internal AI/service)
- ttl: int | None    (seconds the event is considered valid for processing)
- version: str       (our internal schema version)

The event payload is carried in `data` and should be a JSON-serializable object.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class CloudEvent(BaseModel):
    """CloudEvents v1.0 envelope with standard and extension attributes."""

    # Required by spec
    specversion: str = Field(default="1.0")
    id: str = Field(default_factory=lambda: uuid4().hex)
    source: str
    type: str
    time: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    # Optional by spec
    subject: str | None = None
    datacontenttype: str = Field(default="application/json")

    # Data payload
    data: dict[str, Any] = Field(default_factory=dict)

    # Extensions we standardize on
    tenant_id: str | None = None
    employee_id: str | None = None
    trace_id: str | None = None
    actor: str | None = None
    ttl: int | None = Field(default=None, description="Seconds until the event expires for processing")
    version: str = Field(default="1.0")

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.ttl is None or self.ttl <= 0:
            return False
        try:
            ts = datetime.fromisoformat(self.time)
        except Exception:
            return False
        current = now or datetime.now(UTC)
        return ts + timedelta(seconds=int(self.ttl)) < current


def make_event(
    *,
    source: str,
    type: str,
    subject: str | None = None,
    data: dict[str, Any] | None = None,
    tenant_id: str | None = None,
    employee_id: str | None = None,
    trace_id: str | None = None,
    actor: str | None = None,
    ttl: int | None = None,
    version: str = "1.0",
) -> CloudEvent:
    """Create a new CloudEvent with sane defaults."""
    return CloudEvent(
        source=source,
        type=type,
        subject=subject,
        data=data or {},
        tenant_id=tenant_id,
        employee_id=employee_id,
        trace_id=trace_id,
        actor=actor,
        ttl=ttl,
        version=version,
    )


