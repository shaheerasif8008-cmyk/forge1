from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from ..api.auth import get_current_user, decode_access_token
from ..interconnect.cloudevents import CloudEvent
from ..interconnect import get_interconnect


router = APIRouter(prefix="/ai-comms", tags=["ai-comms"])


@router.get("/events")
async def stream_events(
    request: Request,
    type: str | None = Query(default=None),
    employee_id: str | None = Query(default=None),
    token: str | None = Query(default=None),
    user=Depends(get_current_user),  # noqa: B008
):
    """Tenant-scoped live events stream via SSE.

    Only events for the caller's tenant are delivered. Optional filters by type/employee.
    Authorization: Bearer header or `?token=` query param.
    """

    # Authorize: accept Bearer header OR ?token= query param
    caller_tenant = str(user.get("tenant_id", ""))
    if not caller_tenant:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # If token query param is supplied (EventSource cannot add headers), verify it
    if token:
        try:
            payload = decode_access_token(token)
            if str(payload.get("tenant_id", "")) != caller_tenant:
                raise HTTPException(status_code=403, detail="Forbidden")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Unauthorized")

    ic = await get_interconnect()
    stop_event = asyncio.Event()

    async def event_generator():
        queue: asyncio.Queue[CloudEvent] = asyncio.Queue(maxsize=200)

        async def handler(ev: CloudEvent) -> bool:
            # Enforce tenant scoping
            if ev.tenant_id and ev.tenant_id != caller_tenant:
                return True
            if employee_id and ev.employee_id != employee_id:
                return True
            if type and ev.type != type:
                return True
            try:
                queue.put_nowait(ev)
            except asyncio.QueueFull:
                # drop oldest when over capacity
                try:
                    _ = queue.get_nowait()
                except Exception:
                    pass
                try:
                    queue.put_nowait(ev)
                except Exception:
                    pass
            return True

        # Subscribe in background to all relevant event streams
        async def _run():
            tasks = []
            for stream in (
                "events.core",
                "events.tasks",
                "events.employees",
                "events.ops",
                "events.rag",
                "events.security",
            ):
                tasks.append(
                    asyncio.create_task(
                        ic.subscribe(
                            stream=stream,
                            group="client-dashboard",
                            consumer=f"client-{id(stop_event)}",
                            handler=handler,
                            stop_event=stop_event,
                        )
                    )
                )
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                pass

        bg = asyncio.create_task(_run())

        try:
            yield b":ok\n\n"
            while not stop_event.is_set():
                try:
                    ev = await asyncio.wait_for(queue.get(), timeout=10.0)
                    payload = ev.model_dump()
                    data = json.dumps(payload).encode()
                    yield b"event: message\n" + b"data: " + data + b"\n\n"
                except asyncio.TimeoutError:
                    # keep-alive comment
                    yield b":keepalive\n\n"
        finally:
            stop_event.set()
            bg.cancel()

    return StreamingResponse(event_generator(), media_type="text/event-stream")



