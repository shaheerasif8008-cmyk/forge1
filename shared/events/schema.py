from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class EventBase(BaseModel):
    id: str | None = None  # Redis XADD ID assigned on publish
    type: str
    ts: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    tenant_id: str | None = None
    user_id: str | None = None
    employee_id: str | None = None
    source: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class EmployeeCreated(EventBase):
    type: str = Field(default="employee.created", frozen=True)
    data: dict[str, Any] = Field(default_factory=dict)  # {name}


class RunRequested(EventBase):
    type: str = Field(default="run.requested", frozen=True)
    data: dict[str, Any] = Field(default_factory=dict)  # {input_preview}


class ToolCalled(EventBase):
    type: str = Field(default="tool.called", frozen=True)
    data: dict[str, Any] = Field(default_factory=dict)  # {tool_name}


class KeyCreated(EventBase):
    type: str = Field(default="key.created", frozen=True)
    data: dict[str, Any] = Field(default_factory=dict)  # {employee_id, key_id}


class RolloutTriggered(EventBase):
    type: str = Field(default="rollout.triggered", frozen=True)
    data: dict[str, Any] = Field(default_factory=dict)



