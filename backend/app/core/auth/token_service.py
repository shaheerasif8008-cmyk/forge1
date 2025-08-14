"""Access/refresh token minting and rotation using JWT with jose."""

from __future__ import annotations

import hmac
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

from jose import jwt
from sqlalchemy.orm import Session

from ..config import settings
from ...db.models import AuthSession


ALGO = "HS256"


@dataclass(slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    refresh_jti: str


def _now() -> datetime:
    return datetime.now(UTC)


def _hash_token(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _sign(payload: dict[str, Any], key: str, ttl: timedelta) -> str:
    payload = dict(payload)
    payload["exp"] = _now() + ttl
    return jwt.encode(payload, key, algorithm=ALGO)


def mint_access(subject: str, tenant_id: str, roles: list[str] | None = None) -> str:
    ttl = timedelta(minutes=settings.access_token_ttl_minutes)
    claims: dict[str, Any] = {"sub": subject, "tenant_id": tenant_id, "roles": roles or ["user"]}
    jwt_secret = settings.jwt_secret
    if jwt_secret is None and settings.env == "dev":
        jwt_secret = "dev-only-secret-do-not-use-in-production"
    return _sign(claims, jwt_secret, ttl)


def mint_refresh(db: Session, user_id: int, tenant_id: str, session_meta: dict[str, Any] | None = None) -> tuple[str, str]:
    ttl = timedelta(days=settings.refresh_token_ttl_days)
    jti = str(uuid.uuid4())
    claims: dict[str, Any] = {"sub": str(user_id), "tenant_id": tenant_id, "jti": jti, "typ": "refresh"}
    jwt_refresh_secret = settings.jwt_refresh_secret
    if jwt_refresh_secret is None and settings.env == "dev":
        jwt_refresh_secret = "dev-only-refresh-secret-do-not-use-in-production"
    token = _sign(claims, jwt_refresh_secret, ttl)
    token_hash = _hash_token(token)
    session = AuthSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        tenant_id=tenant_id,
        jti=jti,
        refresh_token_hash=token_hash,
        expires_at=_now() + ttl,
        last_ip=(session_meta or {}).get("ip"),
        user_agent=(session_meta or {}).get("ua"),
    )
    db.add(session)
    db.commit()
    return token, jti


def verify_access(token: str) -> dict[str, Any]:
    jwt_secret = settings.jwt_secret
    if jwt_secret is None and settings.env == "dev":
        jwt_secret = "dev-only-secret-do-not-use-in-production"
    return jwt.decode(token, jwt_secret, algorithms=[ALGO], options={"leeway": 60})


def verify_refresh(db: Session, token: str) -> AuthSession | None:
    try:
        jwt_refresh_secret = settings.jwt_refresh_secret
        if jwt_refresh_secret is None:
            jwt_refresh_secret = settings.jwt_secret
            if jwt_refresh_secret is None and settings.env == "dev":
                jwt_refresh_secret = "dev-only-refresh-secret-do-not-use-in-production"
        payload = jwt.decode(token, jwt_refresh_secret, algorithms=[ALGO], options={"leeway": 60})
        if payload.get("typ") != "refresh":
            return None
        jti = str(payload.get("jti", ""))
        sub = str(payload.get("sub", ""))
        if not jti or not sub:
            return None
        token_hash = _hash_token(token)
        session = db.query(AuthSession).filter(AuthSession.jti == jti, AuthSession.refresh_token_hash == token_hash, AuthSession.revoked.is_(False)).first()
        return session
    except Exception:
        return None


def rotate_refresh(db: Session, session: AuthSession) -> str:
    # Revoke old token by marking rotated_at and changing jti/hash
    session.rotated_at = _now()
    session.revoked = True
    db.add(session)
    db.commit()
    # Issue a new refresh linked to same user/tenant
    return mint_refresh(db, user_id=session.user_id, tenant_id=session.tenant_id)[0]


def revoke_all_user_sessions(db: Session, user_id: int) -> int:
    q = db.query(AuthSession).filter(AuthSession.user_id == user_id, AuthSession.revoked.is_(False))
    count = 0
    for s in q.all():
        s.revoked = True
        count += 1
        db.add(s)
    db.commit()
    return count


