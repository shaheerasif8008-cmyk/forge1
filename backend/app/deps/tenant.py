"""Tenant-related dependencies and helpers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..core.flags.feature_flags import is_enabled
from ..db.models import Employee, LongTermMemory, TaskExecution, Tenant
from ..db.session import get_session


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


def beta_gate(flag: str):
    """Dependency factory that ensures tenant is beta and feature flag is enabled.

    Returns 404 when gate conditions are not met to avoid information leaks.
    """

    def _dep(
        current_user: Annotated[dict[str, object], Depends(get_current_user)],
        db: Annotated[Session, Depends(get_session)],
    ) -> None:
        tenant_id = str(current_user.get("tenant_id", ""))
        try:
            tenant = db.get(Tenant, tenant_id)
            if tenant is None or not bool(getattr(tenant, "beta", False)):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
            if not is_enabled(db, tenant_id, flag, default=False):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        except HTTPException:
            raise
        except Exception:  # noqa: BLE001
            # Fail closed to avoid feature enumeration
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        return None

    return _dep

