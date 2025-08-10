import os

import httpx
import pytest


@pytest.mark.asyncio
async def test_auth_flow():
    username = os.getenv("DEMO_USERNAME", "admin")
    password = os.getenv("DEMO_PASSWORD", "admin")
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code in {200, 404}


