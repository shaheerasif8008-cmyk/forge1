from __future__ import annotations

import asyncio
import json
import os

import pytest

from app.core.bus import publish, subscribe


@pytest.mark.asyncio
async def test_publish_consume_cycle(monkeypatch):
    # Use a test Redis DB if provided; otherwise rely on default.
    monkeypatch.setenv("REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/15"))
    evt = {"type": "unit.test", "tenant_id": "t1", "data": {"x": 1}}
    msg_id = await publish(evt)
    assert isinstance(msg_id, str) or msg_id is None
    # If no Redis available, publish returns None and we skip
    if msg_id is None:
        return
    # Consume from last seen (0-0) to include our event
    got = None
    async for mid, ev in subscribe("0-0"):
        if mid == msg_id:
            got = ev
            break
    assert got is not None
    assert got.get("type") == "unit.test"


