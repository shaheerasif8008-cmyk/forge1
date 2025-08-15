from __future__ import annotations

import hmac
import hashlib
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..db.models import WebhookEndpoint, WebhookDelivery
from ..db.session import get_session
from ..core.config import settings


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookIn(BaseModel):
    url: str
    secret: str = Field(min_length=8)
    active: bool = True
    event_types: list[str] | None = None


class WebhookOut(BaseModel):
    id: int
    url: str
    active: bool
    event_types: list[str] | None


def _require_admin(user=Depends(get_current_user)):
    roles = set(user.get("roles", []) if isinstance(user.get("roles", []), list) else [])
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


@router.get("/", response_model=list[WebhookOut])
def list_endpoints(user=Depends(_require_admin), db: Session = Depends(get_session)) -> list[WebhookOut]:  # noqa: B008
    rows = db.query(WebhookEndpoint).filter(WebhookEndpoint.tenant_id == user["tenant_id"]).all()
    return [WebhookOut(id=r.id, url=r.url, active=r.active, event_types=r.event_types) for r in rows]


@router.post("/", response_model=WebhookOut)
def create_endpoint(payload: WebhookIn, user=Depends(_require_admin), db: Session = Depends(get_session)) -> WebhookOut:  # noqa: B008
    row = WebhookEndpoint(tenant_id=user["tenant_id"], url=payload.url, secret=payload.secret, active=payload.active, event_types=payload.event_types)
    db.add(row)
    db.commit()
    return WebhookOut(id=row.id, url=row.url, active=row.active, event_types=row.event_types)


@router.patch("/{endpoint_id}", response_model=WebhookOut)
def update_endpoint(endpoint_id: int, payload: WebhookIn, user=Depends(_require_admin), db: Session = Depends(get_session)) -> WebhookOut:  # noqa: B008
    row: WebhookEndpoint | None = db.get(WebhookEndpoint, endpoint_id)
    if row is None or row.tenant_id != user["tenant_id"]:
        raise HTTPException(status_code=404, detail="Not found")
    row.url = payload.url
    row.secret = payload.secret
    row.active = payload.active
    row.event_types = payload.event_types
    db.add(row)
    db.commit()
    return WebhookOut(id=row.id, url=row.url, active=row.active, event_types=row.event_types)


@router.delete("/{endpoint_id}")
def delete_endpoint(endpoint_id: int, user=Depends(_require_admin), db: Session = Depends(get_session)) -> dict[str, str]:  # noqa: B008
    row: WebhookEndpoint | None = db.get(WebhookEndpoint, endpoint_id)
    if row is None or row.tenant_id != user["tenant_id"]:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()
    return {"status": "deleted"}


class TestPayload(BaseModel):
    event_type: str = "test.ping"
    data: dict[str, Any] = Field(default_factory=lambda: {"hello": "world"})


@router.post("/test")
def send_test(payload: TestPayload, user=Depends(_require_admin), db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    # queue deliveries
    eps = db.query(WebhookEndpoint).filter(WebhookEndpoint.tenant_id == user["tenant_id"], WebhookEndpoint.active == True).all()  # noqa: E712
    enqueued = 0
    for ep in eps:
        d = WebhookDelivery(endpoint_id=ep.id, tenant_id=ep.tenant_id, event_type=payload.event_type, payload=payload.model_dump())
        db.add(d)
        enqueued += 1
    db.commit()
    return {"enqueued": enqueued}


@router.post("/verify")
def verify_signature(body: dict[str, Any], signature: str, secret: str) -> dict[str, Any]:
    # signature format: sha256=hex
    try:
        algo, sig_hex = signature.split("=", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid signature format")
    if algo != "sha256":
        raise HTTPException(status_code=400, detail="unsupported algo")
    mac = hmac.new(secret.encode("utf-8"), digestmod=hashlib.sha256)
    mac.update(("payload:" + str(body)).encode("utf-8"))
    ok = hmac.compare_digest(mac.hexdigest(), sig_hex)
    return {"valid": bool(ok)}


