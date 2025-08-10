from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from ..core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(subject: str, extra_claims: dict[str, str] | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, object] = {"sub": subject, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> dict[str, object]:
    try:
        payload: dict[str, object] = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/login")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> dict[str, str]:
    # Simple stub authentication: accept username with password 'admin'
    if form_data.password != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user_id = "user_123"
    tenant_id = "tenant_abc"
    token = create_access_token(subject=user_id, extra_claims={"tenant_id": tenant_id})
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict[str, str]:
    payload = decode_access_token(token)
    user_id = str(payload.get("sub", ""))
    tenant_id = str(payload.get("tenant_id", ""))
    if not user_id or not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return {"user_id": user_id, "tenant_id": tenant_id}


@router.get("/me")
async def read_me(current_user: Annotated[dict[str, str], Depends(get_current_user)]) -> dict[str, str]:
    return current_user


