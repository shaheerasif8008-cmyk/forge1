from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse

from ..core.config import settings
from .auth import get_current_user, decode_access_token
from ..interconnect.cloudevents import CloudEvent
from ..interconnect import get_interconnect


router = APIRouter(prefix="/admin/ai-comms", tags=["admin"])


def require_admin(  # noqa: ANN001 - dependency
    request: Request,
    token: str | None = Query(default=None),
) -> dict[str, Any]:
    """Authorize admin via Bearer header or ?token= query param.

    - Prefer Authorization: Bearer <jwt>
    - Fallback to token query parameter for compatibility with tooling
    """
    user: dict[str, Any] | None = None

    # Try Authorization header first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_access_token(auth_header.split(" ", 1)[1])
            roles_claim = payload.get("roles", [])
            if isinstance(roles_claim, list):
                roles = [str(r) for r in roles_claim]
            elif isinstance(roles_claim, str) and roles_claim:
                roles = [roles_claim]
            else:
                roles = []
            user = {
                "user_id": str(payload.get("sub", "")),
                "tenant_id": str(payload.get("tenant_id", "")),
                "roles": roles,
            }
        except HTTPException:
            user = None

    # Fallback to token query parameter
    if user is None and token:
        payload = decode_access_token(token)
        roles_claim = payload.get("roles", [])
        if isinstance(roles_claim, list):
            roles = [str(r) for r in roles_claim]
        elif isinstance(roles_claim, str) and roles_claim:
            roles = [roles_claim]
        else:
            roles = []
        user = {
            "user_id": str(payload.get("sub", "")),
            "tenant_id": str(payload.get("tenant_id", "")),
            "roles": roles,
        }

    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    roles_set = set([str(r) for r in (user.get("roles", []) or [])])
    if "admin" not in roles_set:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


@router.get("/events")
async def admin_events(  # noqa: D401 - SSE endpoint
    request: Request,
    _: dict[str, Any] = Depends(require_admin),  # auth enforced via JWT Bearer or token query param
    type: str | None = Query(default=None),
    employee_id: str | None = Query(default=None),
) -> EventSourceResponse:
    """Admin SSE: streams interconnect events; heartbeats every 15s."""
    # If the feature is disabled, expose 404 for admin console cleanliness
    if hasattr(settings, "ai_comms_dashboard_enabled") and not settings.ai_comms_dashboard_enabled:
        raise HTTPException(status_code=404, detail="Feature disabled")

    async def event_iter() -> AsyncIterator[dict[str, Any] | str]:
        queue: asyncio.Queue[CloudEvent] = asyncio.Queue(maxsize=200)
        stop_event = asyncio.Event()

        async def _handler(ev: CloudEvent) -> bool:
            if type and ev.type != type:
                return True
            if employee_id and ev.employee_id != employee_id:
                return True
            try:
                queue.put_nowait(ev)
            except asyncio.QueueFull:
                try:
                    _ = queue.get_nowait()
                except Exception:
                    pass
                try:
                    queue.put_nowait(ev)
                except Exception:
                    pass
            return True

        bg_task: asyncio.Task | None = None
        if getattr(settings, "interconnect_enabled", False):
            try:
                ic = await get_interconnect()
                bg_task = asyncio.create_task(
                    ic.subscribe(
                        stream="events.*",
                        group="admin-dashboard",
                        consumer=f"admin-{id(stop_event)}",
                        handler=_handler,
                        stop_event=stop_event,
                    )
                )
            except Exception:
                # degraded: continue with heartbeats only
                bg_task = None

        try:
            # Initial comment to establish stream
            yield ":ok\n\n"
            while not await request.is_disconnected():
                try:
                    ev = await asyncio.wait_for(queue.get(), timeout=15.0)
                    payload = ev.model_dump()
                    payload_out = {
                        "tenant_id": payload.get("tenant_id"),
                        "employee_id": payload.get("employee_id"),
                        "type": payload.get("type"),
                        "time": payload.get("time"),
                        "trace_id": payload.get("trace_id"),
                        "summary": payload.get("subject") or payload.get("source"),
                    }
                    yield {
                        "event": "message",
                        "data": json.dumps(payload_out, ensure_ascii=False),
                    }
                except asyncio.TimeoutError:
                    # Heartbeat comment
                    yield ":keepalive\n\n"
        finally:
            stop_event.set()
            if bg_task:
                bg_task.cancel()

    return EventSourceResponse(event_iter())

