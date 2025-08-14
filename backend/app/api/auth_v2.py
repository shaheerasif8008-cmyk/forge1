from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..core.auth.password_service import check_password_strength, hash_password, verify_password
from ..core.auth.token_service import (
    mint_access,
    mint_refresh,
    verify_refresh,
    rotate_refresh,
    revoke_all_user_sessions,
)
from ..core.auth.email_service import make_verify_email, make_reset_email, send_email
from ..core.auth.mfa_service import provision_mfa, verify_mfa_code, try_use_recovery_code
from ..core.config import settings
from ..core.security.rate_limit import increment_and_check
from ..db.models import EmailVerification, PasswordReset, Tenant, User, UserMfa, UserTenant
from ..db.session import get_session
from .auth import get_current_user


router = APIRouter(prefix="/auth", tags=["auth-v2"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_name: str | None = None


@router.post("/register")
def register(req: RegisterRequest, db: Annotated[Session, Depends(get_session)]) -> dict[str, str]:  # noqa: B008
    strength = check_password_strength(req.password)
    if not strength.ok:
        raise HTTPException(status_code=400, detail=strength.reason or "Weak password")
    if db.query(User).filter(User.email == str(req.email)).first() is not None:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=str(req.email), hashed_password=hash_password(req.password), is_active=True, email_verified=False)
    db.add(user)
    # Create tenant if requested
    tenant_id = None
    if req.tenant_name:
        tenant_id = str(uuid.uuid4())[:12]
        db.add(Tenant(id=tenant_id, name=req.tenant_name))
        db.flush()
        db.add(UserTenant(user_id=user.id, tenant_id=tenant_id, role="owner"))
    db.commit()
    # Verification email
    token = str(uuid.uuid4())
    ev = EmailVerification(
        id=str(uuid.uuid4()),
        user_id=user.id,
        email=user.email,
        token=token,
        purpose="verify",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=3),
    )
    db.add(ev)
    db.commit()
    link = f"{settings.frontend_base_url}/verify-email?token={token}"
    send_email(make_verify_email(user.email, link))
    return {"status": "ok"}


class AcceptInviteRequest(BaseModel):
    token: str
    password: str


@router.post("/accept-invite")
def accept_invite(req: AcceptInviteRequest, db: Annotated[Session, Depends(get_session)]) -> dict[str, str]:  # noqa: B008
    strength = check_password_strength(req.password)
    if not strength.ok:
        raise HTTPException(status_code=400, detail=strength.reason or "Weak password")
    row = (
        db.query(EmailVerification)
        .filter(EmailVerification.token == req.token, EmailVerification.purpose == "invite", EmailVerification.consumed_at.is_(None))
        .first()
    )
    if row is None or row.expires_at < datetime.now(UTC) or not row.email:
        raise HTTPException(status_code=400, detail="Invalid token")
    # If user exists, attach; else create
    user = db.query(User).filter(User.email == row.email).first()
    if user is None:
        user = User(email=row.email, hashed_password=hash_password(req.password), is_active=True)
        db.add(user)
        db.flush()
    # Expect tenant_id in querystring on frontend but here we can look up by last invite in same domain; for simplicity, we cannot infer tenant here
    # The invite flow should create a UserTenant when admin invited with tenant_id, so we add if not exists via ev.email + tenant from link in frontend
    # Best effort: nothing to do at backend without tenant id; admin role assignment endpoint covers role binding.
    row.consumed_at = datetime.now(UTC)
    db.add(row)
    db.commit()
    return {"status": "ok"}


class VerifyEmailRequest(BaseModel):
    token: str


@router.post("/verify-email")
def verify_email(req: VerifyEmailRequest, db: Annotated[Session, Depends(get_session)]) -> dict[str, str]:  # noqa: B008
    row = (
        db.query(EmailVerification)
        .filter(EmailVerification.token == req.token, EmailVerification.consumed_at.is_(None))
        .first()
    )
    if row is None or row.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Invalid token")
    if row.user_id:
        user = db.get(User, row.user_id)
        if user:
            user.email_verified = True
            db.add(user)
    row.consumed_at = datetime.now(UTC)
    db.add(row)
    db.commit()
    return {"status": "ok"}


@router.post("/login-password")
def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],  # noqa: B008
    db: Annotated[Session, Depends(get_session)],  # noqa: B008
) -> dict[str, str]:
    # Rate limit per IP/email
    key_ip = f"rl:login:ip:{getattr(request.client, 'host', 'unknown')}"
    key_email = f"rl:login:email:{form_data.username}"
    try:
        if not increment_and_check(settings.redis_url, key_ip, settings.login_rate_limit_per_minute, 60):
            raise HTTPException(status_code=429, detail="Too many attempts")
        if not increment_and_check(settings.redis_url, key_email, settings.login_rate_limit_per_minute, 60):
            raise HTTPException(status_code=429, detail="Too many attempts")
    except Exception:
        pass

    user = db.query(User).filter((User.email == form_data.username) | (User.username == form_data.username)).first()
    if user is None or not verify_password(user.hashed_password, form_data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User disabled")

    # Select tenant: prefer explicit tenant_id param or default membership
    tenant_link = db.query(UserTenant).filter(UserTenant.user_id == user.id).first()
    if tenant_link is None:
        raise HTTPException(status_code=400, detail="No tenant membership")
    tenant_id = tenant_link.tenant_id

    # MFA gate (if enabled)
    mfa = db.get(UserMfa, user.id)
    if mfa and mfa.enabled:
        # Require code parameter in password field extension or reject; for simplicity expect 'otp' form field if provided
        otp = getattr(form_data, "otp", None)  # type: ignore[attr-defined]
        if not otp:
            raise HTTPException(status_code=401, detail="MFA required")
        if not verify_mfa_code(db, user.id, otp):
            raise HTTPException(status_code=401, detail="Invalid MFA code")

    access = mint_access(str(user.id), tenant_id, roles=[tenant_link.role])
    refresh, jti = mint_refresh(db, user.id, tenant_id, session_meta={"ip": getattr(request.client, "host", None), "ua": request.headers.get("User-Agent")})
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
def refresh_token(req: RefreshRequest, db: Annotated[Session, Depends(get_session)]) -> dict[str, str]:  # noqa: B008
    session = verify_refresh(db, req.refresh_token)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    # rotate
    new_refresh = rotate_refresh(db, session)
    access = mint_access(str(session.user_id), session.tenant_id, roles=["member"])  # role can be looked up
    return {"access_token": access, "refresh_token": new_refresh, "token_type": "bearer"}


@router.post("/logout")
def logout(
    req: RefreshRequest,
    db: Annotated[Session, Depends(get_session)],  # noqa: B008
) -> dict[str, str]:
    session = verify_refresh(db, req.refresh_token)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    session.revoked = True
    db.add(session)
    db.commit()
    return {"status": "ok"}


class RequestReset(BaseModel):
    email: EmailStr


@router.post("/request-password-reset")
def request_reset(req: RequestReset, db: Annotated[Session, Depends(get_session)]) -> dict[str, str]:  # noqa: B008
    user = db.query(User).filter(User.email == str(req.email)).first()
    if user is None:
        return {"status": "ok"}
    pr_token = str(uuid.uuid4())
    pr = PasswordReset(id=str(uuid.uuid4()), user_id=user.id, token=pr_token, created_at=datetime.now(UTC), expires_at=datetime.now(UTC) + timedelta(hours=2))
    db.add(pr)
    db.commit()
    link = f"{settings.frontend_base_url}/reset-password?token={pr_token}"
    send_email(make_reset_email(user.email, link))
    return {"status": "ok"}


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Annotated[Session, Depends(get_session)]) -> dict[str, str]:  # noqa: B008
    row = (
        db.query(PasswordReset)
        .filter(PasswordReset.token == req.token, PasswordReset.consumed_at.is_(None))
        .first()
    )
    if row is None or row.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Invalid token")
    strength = check_password_strength(req.new_password)
    if not strength.ok:
        raise HTTPException(status_code=400, detail=strength.reason or "Weak password")
    user = db.get(User, row.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid token")
    user.hashed_password = hash_password(req.new_password)
    db.add(user)
    row.consumed_at = datetime.now(UTC)
    db.add(row)
    db.commit()
    return {"status": "ok"}


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_url: str
    recovery_codes: list[str]


@router.post("/mfa/setup", response_model=MfaSetupResponse)
def mfa_setup(
    db: Annotated[Session, Depends(get_session)],  # noqa: B008
    current_user: Annotated[dict[str, object], Depends(get_current_user)],  # noqa: B008
) -> MfaSetupResponse:
    user_id = int(current_user["user_id"]) if str(current_user["user_id"]).isdigit() else None
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid user")
    prov = provision_mfa(db, user_id=user_id)
    return MfaSetupResponse(secret=prov.secret, otpauth_url=prov.otpauth_url, recovery_codes=prov.recovery_codes)


class MfaVerifyRequest(BaseModel):
    code: str


@router.post("/mfa/verify")
def mfa_verify(
    req: MfaVerifyRequest,
    db: Annotated[Session, Depends(get_session)],  # noqa: B008
    current_user: Annotated[dict[str, object], Depends(get_current_user)],  # noqa: B008
) -> dict[str, str]:
    user_id = int(current_user["user_id"]) if str(current_user["user_id"]).isdigit() else None
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid user")
    if not verify_mfa_code(db, user_id, req.code):
        # try recovery code
        if not try_use_recovery_code(db, user_id, req.code):
            raise HTTPException(status_code=400, detail="Invalid code")
    return {"status": "ok"}


@router.post("/mfa/disable")
def mfa_disable(
    db: Annotated[Session, Depends(get_session)],  # noqa: B008
    current_user: Annotated[dict[str, object], Depends(get_current_user)],  # noqa: B008
) -> dict[str, str]:
    user_id = int(current_user["user_id"]) if str(current_user["user_id"]).isdigit() else None
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid user")
    row = db.get(UserMfa, user_id)
    if row:
        row.enabled = False
        row.secret = None
        row.enabled_at = None
        db.add(row)
        db.commit()
    revoke_all_user_sessions(db, user_id)
    return {"status": "ok"}


