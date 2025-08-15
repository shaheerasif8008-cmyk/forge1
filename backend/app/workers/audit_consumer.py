from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.orm import Session

from ..core.bus import subscribe
from ..db.models import AuditLog
from ..db.session import get_session


logger = logging.getLogger(__name__)


async def run_consumer(stop: asyncio.Event | None = None) -> None:
    last_id = "$"
    async for msg_id, ev in subscribe(last_id):
        try:
            tenant_id = str(ev.get("tenant_id") or "") or None
            user_id = ev.get("user_id")
            user_int = int(user_id) if isinstance(user_id, str) and user_id.isdigit() else None
            with next(get_session()) as db:  # type: ignore[misc]
                _persist(db, tenant_id, user_int, ev)
        except Exception:  # noqa: BLE001
            logger.exception("audit consume error")
        # loop continues


def _persist(db: Session, tenant_id: str | None, user_id: int | None, ev: dict[str, Any]) -> None:
    try:
        entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=str(ev.get("type", "event")),
            method="EVENT",
            path=str(ev.get("source", "bus")),
            status_code=200,
            meta=ev,
        )
        db.add(entry)
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()


