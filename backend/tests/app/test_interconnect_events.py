from __future__ import annotations

import asyncio
import os

import pytest

from app.interconnect.cloudevents import make_event
from app.interconnect.sdk import Interconnect


@pytest.mark.asyncio
async def test_publish_and_subscribe_roundtrip(monkeypatch):
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    ic = Interconnect(url)
    cli = await ic.client()
    # Subscribe in background
    received: list[dict] = []
    stop = asyncio.Event()

    async def handler(ev):
        received.append(ev.model_dump())
        stop.set()
        return True

    task = asyncio.create_task(ic.subscribe(stream="events.core", group="tests", consumer="c1", handler=handler))
    await asyncio.sleep(0.2)
    # Publish
    await ic.publish(stream="events.core", type="unittest.event", source="tests", data={"hello": "world"})
    try:
        await asyncio.wait_for(stop.wait(), timeout=5.0)
    finally:
        task.cancel()
    assert any(e["type"] == "unittest.event" for e in received)


