from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Final

from .config import settings


HMAC_ALGO: Final[str] = "sha256"


def sign_bytes(data: bytes) -> str:
    key = settings.report_secret.encode("utf-8")
    digest = hmac.new(key, data, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def verify_bytes(data: bytes, signature_b64: str) -> bool:
    try:
        expected = sign_bytes(data)
        return hmac.compare_digest(expected, signature_b64)
    except Exception:
        return False


