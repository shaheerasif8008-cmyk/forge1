from __future__ import annotations

import asyncio
import os

import pytest

from app.interconnect.sdk import Interconnect
from app.interconnect.redis_streams import RetryPolicy


@pytest.mark.asyncio
async def test_dlq_on_failure(monkeypatch):
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    ic = Interconnect(url)
    cli = await ic.client()
    # Handler always fails
    async def handler(_ev):
        return False

    # Ensure group exists and consume one message leading to DLQ after small max_attempts
    stop = asyncio.Event()

    async def run():
        await ic.subscribe(
            stream="events.tasks",
            group="tests-dlq",
            consumer="c1",
            handler=handler,
            retry=RetryPolicy(max_attempts=1, base_delay_ms=10, max_delay_ms=10),
        )

    task = asyncio.create_task(run())
    await asyncio.sleep(0.1)
    await ic.publish(stream="events.tasks", type="unit.fail", source="tests", data={"x": 1})
    # Give time for retries and DLQ publish
    await asyncio.sleep(2.0)
    task.cancel()
    # Check DLQ has entries
    entries = await cli.xrange("events.tasks.dlq", count=10)
    assert len(entries) >= 1


