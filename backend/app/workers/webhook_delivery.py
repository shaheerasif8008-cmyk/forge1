from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..db.models import WebhookDelivery, WebhookEndpoint
from ..db.session import get_session


logger = logging.getLogger(__name__)


def _sign(secret: str, payload: dict[str, Any]) -> str:
    mac = hmac.new(secret.encode("utf-8"), digestmod=hashlib.sha256)
    mac.update(("payload:" + str(payload)).encode("utf-8"))
    return f"sha256={mac.hexdigest()}"


async def run_delivery_loop(stop: asyncio.Event | None = None) -> None:
    while stop is None or not stop.is_set():
        await _tick()
        await asyncio.sleep(0.5)


async def _tick() -> None:
    # Pick due deliveries and attempt
    with next(get_session()) as db:  # type: ignore[misc]
        now = datetime.now(UTC)
        rows = (
            db.query(WebhookDelivery)
            .filter((WebhookDelivery.status == "queued") | ((WebhookDelivery.status == "failed") & (WebhookDelivery.next_attempt_at <= now)))
            .limit(20)
            .all()
        )
        for d in rows:
            _attempt_delivery(db, d)


def _attempt_delivery(db: Session, d: WebhookDelivery) -> None:
    ep: WebhookEndpoint | None = db.get(WebhookEndpoint, d.endpoint_id)
    if ep is None or not ep.active:
        d.status = "dlq"
        db.add(d)
        db.commit()
        return
    headers = {
        "Content-Type": "application/json",
        "X-Forge1-Event": d.event_type,
        "X-Forge1-Signature": _sign(ep.secret, d.payload),
    }
    d.signature = headers["X-Forge1-Signature"]
    try:
        with httpx.Client(timeout=5.0, follow_redirects=False) as client:
            resp = client.post(ep.url, json=d.payload, headers=headers)
            d.attempts += 1
            d.last_status_code = resp.status_code
            if resp.status_code == 410:
                # disable endpoint
                ep.active = False
                d.status = "dlq"
            elif 200 <= resp.status_code < 300:
                d.status = "delivered"
            else:
                # schedule retry with exponential backoff
                backoff = min(60, 2 ** min(6, d.attempts))
                d.status = "failed"
                d.next_attempt_at = datetime.now(UTC) + timedelta(seconds=backoff)
            db.add(ep)
            db.add(d)
            db.commit()
    except Exception as e:  # noqa: BLE001
        d.attempts += 1
        d.status = "failed"
        d.last_error = str(e)
        d.next_attempt_at = datetime.now(UTC) + timedelta(seconds=min(60, 2 ** min(6, d.attempts)))
        db.add(d)
        db.commit()


