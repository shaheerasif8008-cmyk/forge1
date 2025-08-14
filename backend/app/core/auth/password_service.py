"""Password hashing, verification, and strength checking using Argon2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from argon2 import PasswordHasher, exceptions as argon2_exceptions


_PH: Final[PasswordHasher] = PasswordHasher()


@dataclass(slots=True)
class PasswordStrength:
    ok: bool
    reason: str | None = None


def check_password_strength(password: str) -> PasswordStrength:
    if len(password) < 12:
        return PasswordStrength(False, "Password must be at least 12 characters long")
    classes = sum([any(c.islower() for c in password), any(c.isupper() for c in password), any(c.isdigit() for c in password), any(not c.isalnum() for c in password)])
    if classes < 3:
        return PasswordStrength(False, "Use at least three character classes: lower, upper, digit, symbol")
    return PasswordStrength(True)


def hash_password(password: str) -> str:
    return _PH.hash(password)


def verify_password(hashed_password: str, password: str) -> bool:
    try:
        return _PH.verify(hashed_password, password)
    except argon2_exceptions.VerifyMismatchError:
        return False
    except Exception:
        return False


