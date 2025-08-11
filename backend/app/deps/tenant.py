"""Tenant-related dependencies and helpers."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status

from ..api.auth import get_current_user
from ..db.models import Employee, LongTermMemory, TaskExecution


def get_tenant_id(current_user: Annotated[dict[str, str], Depends(get_current_user)]) -> str:
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing tenant")
    return tenant_id


def tenant_filter_for_employee(tenant_id: str):  # noqa: ANN201 - SQLAlchemy expression helper
    return Employee.tenant_id == tenant_id


def tenant_filter_for_task(tenant_id: str):  # noqa: ANN201 - SQLAlchemy expression helper
    return TaskExecution.tenant_id == tenant_id


def tenant_filter_for_long_term_memory(tenant_id: str):  # noqa: ANN201 - SQLAlchemy expression helper
    return LongTermMemory.tenant_id == tenant_id


