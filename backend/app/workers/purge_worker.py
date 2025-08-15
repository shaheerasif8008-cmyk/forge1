from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import logging
from typing import Iterable

from sqlalchemy.orm import Session

from ..db.models import DataLifecyclePolicy, TaskExecution, AuditLog
from ..db.session import get_session


logger = logging.getLogger(__name__)


async def run_purge_loop(stop: asyncio.Event | None = None, interval_seconds: int = 3600) -> None:
    while stop is None or not stop.is_set():
        try:
            purge_once()
        except Exception:  # noqa: BLE001
            logger.exception("purge_once error")
        await asyncio.sleep(interval_seconds)


def purge_once() -> None:
    with next(get_session()) as db:  # type: ignore[misc]
        tenants = [t.tenant_id for t in db.query(DataLifecyclePolicy).all()]
        for tenant_id in tenants:
            _purge_tenant(db, tenant_id)


def _purge_tenant(db: Session, tenant_id: str) -> None:
    p: DataLifecyclePolicy | None = db.get(DataLifecyclePolicy, tenant_id)
    if p is None:
        return
    now = datetime.now(UTC)
    if p.chat_ttl_days and p.chat_ttl_days >= 0:
        cutoff = now - timedelta(days=p.chat_ttl_days)
        try:
            db.query(TaskExecution).filter(TaskExecution.tenant_id == tenant_id, TaskExecution.created_at < cutoff).delete(synchronize_session=False)
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
    if p.tool_io_ttl_days and p.tool_io_ttl_days >= 0:
        cutoff = now - timedelta(days=p.tool_io_ttl_days)
        try:
            db.query(AuditLog).filter(AuditLog.tenant_id == tenant_id, AuditLog.timestamp < cutoff).delete(synchronize_session=False)
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()


