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
        @property
        def content(self) -> bytes:  # pragma: no cover
            return b"{}"

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


def test_api_caller_rejects_non_http(monkeypatch):
    tool = APICaller()
    try:
        tool.execute(method="GET", url="file:///etc/passwd")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_api_caller_retries_on_500(monkeypatch):
    tool = APICaller()

    class DummyResponse:
        def __init__(self, status_code: int, text: str = "ok") -> None:
            self.status_code = status_code
            self._text = text
            self.headers = {"content-type": "application/json"}

        def raise_for_status(self) -> None:  # noqa: D401
            if self.status_code >= 400:
                raise httpx.HTTPStatusError("err", request=None, response=None)

        def json(self):  # noqa: D401
            return {"ok": True}

        @property
        def text(self) -> str:  # noqa: D401
            return self._text
        @property
        def content(self) -> bytes:  # pragma: no cover
            return b"{}"

    class DummyClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN001
            self.calls = 0

        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *args, **kwargs):  # noqa: ANN001, ANN204
            return None

        def request(self, method, url, params=None, json=None):  # noqa: ANN001
            self.calls += 1
            # first call 500, then success
            if self.calls == 1:
                return DummyResponse(500)
            return DummyResponse(200)

    monkeypatch.setattr(httpx, "Client", DummyClient)
    out = tool.execute(method="GET", url="https://example.com", retries=1, timeout=1)
    assert out["status_code"] == 200
