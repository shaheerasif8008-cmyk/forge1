from __future__ import annotations

from datetime import UTC, datetime, timedelta
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.models import EmailVerification, Tenant, User, UserTenant, AuthSession
from ..db.session import get_session
from ..api.auth import get_current_user


router = APIRouter(prefix="/admin", tags=["admin-auth"])  # admin users & sessions


def require_roles(*roles: str):  # noqa: ANN001 - dependency factory
    def _dep(current_user: Annotated[dict[str, object], Depends(get_current_user)]) -> None:
        user_roles = set([str(r) for r in (current_user.get("roles", []) or [])])
        if not any(r in user_roles for r in roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return None

    return _dep


class InviteRequest(BaseModel):
    email: str
    tenant_id: str
    role: str = "member"


@router.post("/users/invite")
def invite_user(
    req: InviteRequest,
    db: Annotated[Session, Depends(get_session)],  # noqa: B008
    _: Annotated[None, Depends(require_roles("admin"))],  # noqa: B008
) -> dict[str, str]:
    tenant = db.get(Tenant, req.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    token = str(uuid.uuid4())
    ev = EmailVerification(
        id=str(uuid.uuid4()),
        user_id=None,
        email=req.email,
        token=token,
        purpose="invite",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.add(ev)
    db.commit()
    # Build acceptance link
    link = f"{settings.frontend_base_url}/accept-invite?token={token}&tenant_id={req.tenant_id}&role={req.role}"
    from ..core.auth.email_service import make_invite_email, send_email

    send_email(make_invite_email(req.email, link, tenant.name))
    return {"status": "ok", "token": token, "link": link}


class RoleRequest(BaseModel):
    role: str


@router.post("/users/{user_id}/role")
def set_user_role(
    user_id: int,
    req: RoleRequest,
    db: Annotated[Session, Depends(get_session)],  # noqa: B008
    current_user: Annotated[dict[str, object], Depends(get_current_user)],  # noqa: B008
) -> dict[str, str]:
    # Tenant-scoped role assignment
    tenant_id = str(current_user.get("tenant_id"))
    membership = (
        db.query(UserTenant)
        .filter(UserTenant.user_id == user_id, UserTenant.tenant_id == tenant_id)
        .first()
    )
    if membership is None:
        membership = UserTenant(user_id=user_id, tenant_id=tenant_id, role=req.role)
    else:
        membership.role = req.role
    db.add(membership)
    db.commit()
    return {"status": "ok"}


@router.get("/users")
def list_users(
    db: Annotated[Session, Depends(get_session)],  # noqa: B008
    current_user: Annotated[dict[str, object], Depends(get_current_user)],  # noqa: B008
) -> list[dict[str, object]]:
    tenant_id = str(current_user.get("tenant_id"))
    rows = (
        db.query(User, UserTenant)
        .join(UserTenant, UserTenant.user_id == User.id)
        .filter(UserTenant.tenant_id == tenant_id)
        .all()
    )
    out: list[dict[str, object]] = []
    for u, ut in rows:
        out.append({"id": u.id, "email": u.email, "role": ut.role})
    return out


@router.post("/sessions/{session_id}/revoke")
def revoke_session(
    session_id: str,
    db: Annotated[Session, Depends(get_session)],  # noqa: B008
    _: Annotated[None, Depends(require_roles("admin"))],  # noqa: B008
) -> dict[str, str]:
    s = db.get(AuthSession, session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Not found")
    s.revoked = True
    db.add(s)
    db.commit()
    return {"status": "ok"}


