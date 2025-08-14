from __future__ import annotations

import hmac
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from ...db.models import EmployeeKey, Employee


def _pepper(env_pepper: str | None) -> str:
    return env_pepper or "dev-employee-keys-pepper"


def hash_secret(prefix: str, secret: str, *, pepper: str | None) -> str:
    """Derive a hex digest used for persistent storage of the employee key secret.

    Uses HMAC-SHA256 with an application-wide pepper and incorporates the key prefix.
    """
    message = f"{prefix}:{secret}".encode()
    key = _pepper(pepper).encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def generate_key_pair(*, pepper: str | None = None) -> tuple[str, str, str]:
    """Create a new (prefix, secret_once, hashed_secret)."""
    # Short prefix helps identify key without exposing the secret
    prefix = secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:12]
    # 32-byte URL-safe secret
    secret_once = secrets.token_urlsafe(24)
    hashed = hash_secret(prefix, secret_once, pepper=pepper)
    return prefix, secret_once, hashed


@dataclass
class EmployeePrincipal:
    employee_key_id: str
    tenant_id: str
    employee_id: str
    scopes: dict[str, Any]


def parse_employee_key_header(value: str | None) -> tuple[str, str] | None:
    """Parse header of the form 'EK_<prefix>.<secret>' and return (prefix, secret)."""
    if not value or not value.startswith("EK_"):
        return None
    try:
        payload = value[3:]
        prefix, secret = payload.split(".", 1)
        if not prefix or not secret:
            return None
        return prefix, secret
    except Exception:
        return None


def authenticate_employee_key(
    header_value: str | None, *, db: Session, pepper: str | None
) -> EmployeePrincipal | None:
    parsed = parse_employee_key_header(header_value)
    if parsed is None:
        return None
    prefix, secret = parsed
    row: EmployeeKey | None = (
        db.query(EmployeeKey).filter(EmployeeKey.prefix == prefix).first()
    )
    if row is None:
        return None
    if row.status != "active":
        return None
    if row.expires_at is not None and row.expires_at < datetime.now(UTC):
        return None
    expected = row.hashed_secret
    candidate = hash_secret(prefix, secret, pepper=pepper)
    if not hmac.compare_digest(expected, candidate):
        return None
    # Confirm employee exists and is tenant-scoped
    emp: Employee | None = db.get(Employee, row.employee_id)
    if emp is None:
        return None
    return EmployeePrincipal(
        employee_key_id=row.id,
        tenant_id=emp.tenant_id,
        employee_id=emp.id,
        scopes=row.scopes or {},
    )


