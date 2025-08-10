from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

from .config import settings


def create_access_token(subject: str, expires_delta_minutes: Optional[int] = None) -> str:
    expire_minutes = (
        expires_delta_minutes if expires_delta_minutes is not None else settings.access_token_expire_minutes
    )
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    to_encode: Dict[str, Any] = {"sub": subject, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    return payload


