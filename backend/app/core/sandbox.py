from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import logging
from typing import Any

from sqlalchemy.orm import Session

from ..db.session import SessionLocal
from ..db.models import Employee, LongTermMemory


logger = logging.getLogger(__name__)


async def start_sandbox_cleanup_worker(stop_event: asyncio.Event | None = None, interval_seconds: int = 60) -> None:
    """Background worker that deletes expired sandbox (lab) employees and their scratch RAG.

    Expects sandbox marker under Employee.config: {"lab": true, "sandbox_id": str, "lab_expires_at": ISO8601}.
    """

    stop = stop_event or asyncio.Event()

    async def _tick_once() -> None:
        try:
            with SessionLocal() as db:
                _cleanup_expired_sandboxes(db)
        except Exception as e:  # noqa: BLE001
            logger.warning("sandbox cleanup tick failed", exc_info=e)

    while not stop.is_set():
        await _tick_once()
        try:
            await asyncio.wait_for(stop.wait(), timeout=max(1, int(interval_seconds)))
        except asyncio.TimeoutError:
            continue


def _cleanup_expired_sandboxes(db: Session) -> None:
    now = datetime.now(UTC)
    rows = db.query(Employee).all()
    deleted: int = 0
    for emp in rows:
        cfg: dict[str, Any] = dict(emp.config or {})
        if not cfg.get("lab"):
            continue
        exp_str = cfg.get("lab_expires_at")
        sid = cfg.get("sandbox_id")
        if not exp_str or not sid:
            continue
        try:
            exp = datetime.fromisoformat(str(exp_str))
        except Exception:
            continue
        if exp <= now:
            # Delete LongTermMemory entries tagged with this sandbox
            try:
                for ltm in (
                    db.query(LongTermMemory)
                    .filter(LongTermMemory.meta.contains({"sandbox_id": sid}))
                    .all()
                ):
                    db.delete(ltm)
            except Exception:
                pass
            # Delete employee
            try:
                db.delete(emp)
                db.commit()
                deleted += 1
            except Exception:
                db.rollback()
    if deleted:
        logger.info("sandbox cleanup removed %s employees", deleted)



