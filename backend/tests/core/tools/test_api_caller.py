from __future__ import annotations

from typing import Any

import httpx

from app.core.tools.builtins.api_caller import APICaller


def test_api_caller_success(monkeypatch):
    tool = APICaller()

    class DummyResponse:
        status_code = 200
        headers = {"x": "y"}

        def raise_for_status(self) -> None:  # noqa: D401
            return

        def json(self) -> dict[str, Any]:
            return {"ok": True}

        @property
        def text(self) -> str:  # pragma: no cover
            return ""

    class DummyClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> DummyClient:
            return self

        def __exit__(self, *args: Any, **kwargs: Any) -> None:
            return None

        def request(
            self, method: str, url: str, headers=None, params=None, json=None
        ):  # noqa: ANN001
            return DummyResponse()

    monkeypatch.setattr(httpx, "Client", DummyClient)
    out = tool.execute(method="GET", url="https://example.com")
    assert out["status_code"] == 200
