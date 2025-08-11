from __future__ import annotations

from typing import Any

import httpx

from ..base_tool import BaseTool


class APICaller(BaseTool):
    """Generic HTTP request executor.

    Accepts method, url, headers, params, json_body, timeout.
    Returns a dict with status_code, headers, data.
    """

    name = "api_caller"
    description = "Execute generic HTTP requests (GET, POST, PUT, DELETE)."

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        method = str(kwargs.get("method", "GET"))
        url = str(kwargs.get("url", ""))
        headers = kwargs.get("headers")
        params = kwargs.get("params")
        json_body = kwargs.get("json_body")
        timeout = float(kwargs.get("timeout", 30.0))

        method_norm = method.upper().strip()
        if not url:
            raise ValueError("url is required")

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.request(method_norm, url, headers=headers, params=params, json=json_body)
            resp.raise_for_status()
            try:
                data = resp.json()
            except Exception:  # noqa: BLE001
                data = {"text": resp.text}
            return {"status_code": resp.status_code, "headers": dict(resp.headers), "data": data}


TOOLS = {APICaller.name: APICaller()}
