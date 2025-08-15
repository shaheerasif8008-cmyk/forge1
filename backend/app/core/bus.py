from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator

import redis.asyncio as redis  # type: ignore

from .config import settings


logger = logging.getLogger(__name__)

STREAM_NAME = "forge1-events"


async def _client() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


async def publish(event: dict[str, Any]) -> str | None:
    """Publish an event to the central stream. Returns the XADD ID."""
    try:
        client = await _client()
        # flatten JSON fields for stream
        fields = {k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v)) for k, v in event.items()}
        msg_id: str = await client.xadd(STREAM_NAME, fields, maxlen=10000, approximate=True)
        return msg_id
    except Exception as e:  # noqa: BLE001
        logger.warning("event publish failed", exc_info=e)
        return None


async def subscribe(last_id: str = "$") -> AsyncGenerator[tuple[str, dict[str, Any]], None]:
    """Subscribe to stream from last_id; yields (id, event_dict)."""
    client = await _client()
    cursor = last_id
    while True:
        try:
            resp = await client.xread({STREAM_NAME: cursor}, block=1000, count=10)
            if not resp:
                continue
            _, messages = resp[0]
            for msg_id, kv in messages:
                try:
                    ev: dict[str, Any] = {}
                    for k, v in kv.items():
                        try:
                            ev[k] = json.loads(v)
                        except Exception:
                            ev[k] = v
                    yield msg_id, ev
                finally:
                    cursor = msg_id
        except Exception as e:  # noqa: BLE001
            logger.warning("event subscribe loop error", exc_info=e)


