from __future__ import annotations

import asyncio
import logging
from typing import Optional

from ..core.config import settings
from .sdk import Interconnect

_singleton_lock = asyncio.Lock()
_ic: Optional[Interconnect] = None
logger = logging.getLogger(__name__)


async def get_interconnect() -> Interconnect:
    global _ic
    if _ic is None:
        async with _singleton_lock:
            if _ic is None:
                _ic = Interconnect(settings.redis_url)
                try:
                    await _ic.client()
                except Exception as e:  # noqa: BLE001
                    logger.error("Interconnect init failed", exc_info=e)
                    raise
    return _ic


