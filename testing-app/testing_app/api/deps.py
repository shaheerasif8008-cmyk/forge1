from __future__ import annotations

from fastapi import Header, HTTPException, status

from testing_app.core.config import settings


def require_service_key(x_testing_service_key: str | None = Header(default=None)) -> None:
    expected = (settings.service_key or "").strip()
    if expected:
        if (x_testing_service_key or "").strip() != expected:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid service key")
    return None


