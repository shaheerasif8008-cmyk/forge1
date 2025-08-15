from __future__ import annotations

from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..core.bus import subscribe


router = APIRouter(prefix="/events", tags=["events"])


@router.get("/stream")
async def stream_events() -> StreamingResponse:
    async def event_gen() -> AsyncGenerator[bytes, None]:
        async for _msg_id, ev in subscribe("$"):
            yield (f"data: {ev}\n\n").encode("utf-8")
    return StreamingResponse(event_gen(), media_type="text/event-stream")



