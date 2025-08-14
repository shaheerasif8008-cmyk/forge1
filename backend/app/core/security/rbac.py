"""RBAC helpers for route protection and tenant scoping."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status

from ...api.auth import get_current_user


def require_roles(*roles: str):  # noqa: ANN001 - dependency factory
    """Dependency that ensures current user has at least one of the required roles."""

    required = {r for r in roles}

    def _dep(current_user: Annotated[dict[str, object], Depends(get_current_user)]) -> None:  # noqa: B008
        user_roles = set([str(r) for r in (current_user.get("roles", []) or [])])
        if required and user_roles.isdisjoint(required):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return None

    return _dep


