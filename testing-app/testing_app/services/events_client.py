from __future__ import annotations

from typing import Any, Callable

import httpx


def subscribe_sse(base_url: str, token: str | None, handler: Callable[[dict[str, Any]], None]) -> None:
    # Best-effort simple SSE subscriber to Forge1 events
    url = f"{base_url.rstrip('/')}/api/v1/ai-comms/events"
    params = {}
    headers = {"Accept": "text/event-stream"}
    if token:
        # EventSource typically requires token in query
        params["token"] = token
    with httpx.Client(timeout=None) as client:
        with client.stream("GET", url, headers=headers, params=params) as resp:
            resp.raise_for_status()
            buf = b""
            for data in resp.iter_bytes():
                if not data:
                    continue
                buf += data
                while b"\n\n" in buf:
                    chunk, buf = buf.split(b"\n\n", 1)
                    try:
                        # Expect lines like: event: message\ndata: {...}
                        for line in chunk.split(b"\n"):
                            if line.startswith(b"data: "):
                                payload = line.split(b": ", 1)[1]
                                import json as _json
                                ev = _json.loads(payload)
                                handler(ev)
                    except Exception:
                        # Best-effort; ignore parse errors
                        pass


