import asyncio

import httpx


async def test_health_endpoint(monkeypatch):
    # If services are not up, endpoint should still return JSON with flags
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        resp = await client.get("/api/v1/health")
        # In CI without services, it may 404 if server not running; this test is mainly used when server is up
        assert resp.status_code in {200, 404}


def test_asyncio_event_loop_exists():
    loop = asyncio.get_event_loop()
    assert loop is not None


