"""TOTP MFA provisioning and verification with recovery codes."""

from __future__ import annotations

import base64
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Iterable

import pyotp
from sqlalchemy.orm import Session

from ...db.models import UserMfa, UserRecoveryCode


def _now() -> datetime:
    return datetime.now(UTC)


def _hash_code(code: str) -> str:
    return sha256(code.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class MfaProvision:
    secret: str
    otpauth_url: str
    recovery_codes: list[str]


def provision_mfa(db: Session, user_id: int, issuer: str = "Forge1") -> MfaProvision:
    secret = base64.b32encode(os.urandom(20)).decode("utf-8").rstrip("=")
    totp = pyotp.TOTP(secret)
    otpauth_url = totp.provisioning_uri(name=str(user_id), issuer_name=issuer)
    # Store secret disabled until verified
    row = db.get(UserMfa, user_id)
    if row is None:
        row = UserMfa(user_id=user_id, secret=secret, enabled=False, created_at=_now())
    else:
        row.secret = secret
        row.enabled = False
    db.add(row)
    # Generate recovery codes
    recovery_codes = [secrets.token_urlsafe(10) for _ in range(8)]
    for code in recovery_codes:
        db.add(UserRecoveryCode(id=str(uuid.uuid4()), user_id=user_id, code_hash=_hash_code(code), created_at=_now()))
    db.commit()
    return MfaProvision(secret=secret, otpauth_url=otpauth_url, recovery_codes=recovery_codes)


def verify_mfa_code(db: Session, user_id: int, code: str) -> bool:
    row = db.get(UserMfa, user_id)
    if row is None or not row.secret:
        return False
    totp = pyotp.TOTP(row.secret)
    ok = bool(totp.verify(code, valid_window=1))
    if ok and not row.enabled:
        row.enabled = True
        row.enabled_at = _now()
        db.add(row)
        db.commit()
    return ok


def try_use_recovery_code(db: Session, user_id: int, code: str) -> bool:
    code_hash = _hash_code(code)
    row = db.query(UserRecoveryCode).filter(UserRecoveryCode.user_id == user_id, UserRecoveryCode.code_hash == code_hash, UserRecoveryCode.used_at.is_(None)).first()
    if row is None:
        return False
    row.used_at = _now()
    db.add(row)
    db.commit()
    return True


