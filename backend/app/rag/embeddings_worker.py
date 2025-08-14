from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from redis import Redis
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.models import RagChunk, RagJob
from ..db.session import SessionLocal

logger = logging.getLogger(__name__)

QUEUE_KEY = "rag:embed:queue"
DLQ_KEY = "rag:embed:dlq"


def _embed(text: str) -> list[float]:
    # Use the existing deterministic hash-based embedding to avoid external deps
    from ..core.memory.long_term import _get_embedding as _emb

    return _emb(text)


async def run_embeddings_worker(stop_event: asyncio.Event | None = None) -> None:
    stop = stop_event or asyncio.Event()
    r = Redis.from_url(settings.redis_url, decode_responses=True)
    while not stop.is_set():
        try:
            item = r.brpop(QUEUE_KEY, timeout=2)
            if not item:
                await asyncio.sleep(0.1)
                continue
            _k, payload = item
            task = json.loads(payload)
            chunk_id = str(task.get("chunk_id"))
            with SessionLocal() as db:
                try:
                    RagChunk.__table__.create(bind=db.get_bind(), checkfirst=True)
                    ch = db.get(RagChunk, chunk_id)
                    if not ch:
                        continue
                    ch.embedding = _embed(ch.content)
                    db.add(ch)
                    db.commit()
                except Exception as e:  # noqa: BLE001
                    db.rollback()
                    r.lpush(DLQ_KEY, payload)
                    logger.warning("embed failed; pushed to DLQ: %s", e)
        except Exception as e:  # noqa: BLE001
            logger.warning("worker loop error: %s", e)
            await asyncio.sleep(0.5)


