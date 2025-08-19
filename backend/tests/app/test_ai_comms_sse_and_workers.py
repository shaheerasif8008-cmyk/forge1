from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.auth import create_access_token
from app.db.models import Tenant, Employee
from app.db.session import SessionLocal
from app.interconnect import get_interconnect


@pytest.mark.asyncio
async def test_employee_created_triggers_central_ai_and_sse_stream(monkeypatch):
    # Ensure dev env behavior
    monkeypatch.setenv("ENV", "dev")

    # Create tenant and employee directly in DB
    tenant_id = "default"
    emp_name = "sse_test_emp"
    with SessionLocal() as db:
        if db.get(Tenant, tenant_id) is None:
            db.add(Tenant(id=tenant_id, name="Default Tenant"))
            db.commit()
        # Deterministic ID as in API
        import hashlib

        emp_id = hashlib.sha1(f"{tenant_id}::{emp_name}".encode()).hexdigest()[:16]
        if db.get(Employee, emp_id) is None:
            db.add(
                Employee(
                    id=emp_id,
                    tenant_id=tenant_id,
                    owner_user_id=None,
                    name=emp_name,
                    config={"role": {"name": "researcher", "description": "desc"}, "defaults": {}} ,
                )
            )
            db.commit()

    ic = await get_interconnect()
    stop = asyncio.Event()
    got_dry_run: asyncio.Event = asyncio.Event()
    received: list[dict] = []

    async def _handler(ev):
        d = ev.model_dump()
        received.append(d)
        if d.get("type") in {"employee.dry_run.completed", "employee.dry_run.failed"} and d.get("employee_id") == emp_id:
            got_dry_run.set()
        return True

    # Subscribe in background to employees stream
    sub_task = asyncio.create_task(ic.subscribe(stream="events.employees", group="tests-ci", consumer="c1", handler=_handler, stop_event=stop))

    # Publish employee.created to kick central AI
    await ic.publish(stream="events.employees", type="employee.created", source="tests", subject=emp_id, tenant_id=tenant_id, employee_id=emp_id)

    try:
        await asyncio.wait_for(got_dry_run.wait(), timeout=15.0)
    finally:
        stop.set()
        sub_task.cancel()

    assert any(e.get("type") in {"employee.dry_run.completed", "employee.dry_run.failed"} for e in received)

    # Now test SSE: build an admin JWT and stream a couple of messages
    jwt = create_access_token("1", {"tenant_id": tenant_id, "roles": ["admin"]})
    with TestClient(app) as client:
        with client.stream("GET", f"/api/v1/admin/ai-comms/events?token={jwt}") as r:
            # Read a few bytes to ensure stream is alive
            chunk = next(r.iter_bytes(), b"")
            assert r.status_code in (200,)
            assert (b":ok" in chunk) or (b"data:" in chunk)


