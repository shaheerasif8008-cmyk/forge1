from __future__ import annotations

import asyncio
import os

import pytest

from app.interconnect.sdk import Interconnect


@pytest.mark.asyncio
async def test_rpc_timeout(monkeypatch):
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    ic = Interconnect(url)
    # No server registered -> should timeout and return None
    res = await ic.rpc_call(method="unknown.method", params={}, timeout_ms=500)
    assert res is None


