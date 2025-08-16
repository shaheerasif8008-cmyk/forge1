from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
import logging
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.models import User
from ..db.session import get_session

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(subject: str, extra_claims: dict[str, object] | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, object] = {"sub": subject, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    # Use fallback secret in dev if JWT_SECRET not set
    jwt_secret = settings.jwt_secret
    if jwt_secret is None and settings.env in {"dev", "local"}:
        jwt_secret = "dev-only-secret-do-not-use-in-production"
    token = jwt.encode(payload, jwt_secret, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> dict[str, object]:
    try:
        # Use fallback secret in dev if JWT_SECRET not set
        jwt_secret = settings.jwt_secret
        if jwt_secret is None and settings.env in {"dev", "local"}:
            jwt_secret = "dev-only-secret-do-not-use-in-production"
        # allow small leeway for clock skew
        payload: dict[str, object] = jwt.decode(
            token,
            jwt_secret,
            algorithms=[ALGORITHM],
            options={"leeway": 60},
        )
        return payload
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


router = APIRouter(prefix="/auth", tags=["auth-legacy"])  # legacy minimal auth kept for backward compat in tests
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
logger = logging.getLogger(__name__)


class MeResponse(BaseModel):
    user_id: str
    tenant_id: str
    email: str | None = None
    username: str | None = None
    roles: list[str] = []


@router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_session),  # noqa: B008
) -> dict[str, str]:
    # Simple auth: find user by username/email; accept password 'admin' (demo only)
    username_or_email = form_data.username
    if not username_or_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username required")

    # Block demo password in non-dev environments (determine env dynamically to honor test monkeypatch)
    import os as _os
    current_env = _os.getenv("ENV", settings.env)
    if current_env not in {"dev", "local"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Login disabled in this environment")
    if form_data.password != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user: User | None = None
    try:
        user = (
            db.query(User)
            .filter((User.username == username_or_email) | (User.email == username_or_email))
            .first()
        )
    except Exception:  # noqa: BLE001
        user = None

    if user is not None:
        user_id = str(user.id)
        tenant_id = user.tenant_id or "default"
        primary_role = user.role if hasattr(user, "role") else ("admin" if user.is_superuser else "user")
        roles: list[str] = []
        if user.is_superuser:
            roles.append("admin")
        if primary_role and primary_role not in roles:
            roles.append(primary_role)
        if not roles:
            roles = ["user"]
    else:
        # Strictly dev-only fallback
        if current_env in {"dev", "local"}:
            user_id = "1"
            tenant_id = "default"
            # Grant admin in dev fallback to enable admin routes during local/testing flows
            roles = ["admin"]
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Login disabled in this environment")

    token = create_access_token(subject=user_id, extra_claims={"tenant_id": tenant_id, "roles": roles})
    logger.info("User logged in")
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict[str, object]:
    payload = decode_access_token(token)
    user_id = str(payload.get("sub", ""))
    tenant_id = str(payload.get("tenant_id", ""))
    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )
    roles_claim = payload.get("roles", [])
    if isinstance(roles_claim, list):
        roles = [str(r) for r in roles_claim]
    elif isinstance(roles_claim, str) and roles_claim:
        roles = [roles_claim]
    else:
        roles = []
    return {"user_id": user_id, "tenant_id": tenant_id, "roles": roles}


@router.get("/me", response_model=MeResponse)
async def read_me(
    current_user: Annotated[dict[str, object], Depends(get_current_user)],
    db: Session = Depends(get_session),  # noqa: B008
) -> MeResponse:
    # Fetch user email/username for convenience; tolerate DB issues
    email: str | None = None
    username: str | None = None
    try:
        uid = int(current_user["user_id"]) if current_user["user_id"].isdigit() else None
        if uid is not None:
            user = db.get(User, uid)
            if user is not None:
                email = user.email
                username = user.username
    except Exception:  # noqa: BLE001
        pass

    return MeResponse(
        user_id=str(current_user["user_id"]),
        tenant_id=str(current_user["tenant_id"]),
        email=email,
        username=username,
        roles=[str(r) for r in (current_user.get("roles", []) or [])] if isinstance(current_user.get("roles", []), list) else [],
    )
