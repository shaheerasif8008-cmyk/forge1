from __future__ import annotations

import httpx
import pytest

from app.core.tools.builtins.web_scraper import WebScraper


class FakeResponse:
    def __init__(self, total_bytes: int) -> None:
        self._total = total_bytes
        self._sent = 0
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.encoding = "utf-8"

    def raise_for_status(self) -> None:  # pragma: no cover - simple
        pass

    def iter_bytes(self):  # type: ignore[override]
        chunk = b"<html>" + b"x" * 1024
        while self._sent < self._total:
            to_send = min(len(chunk), self._total - self._sent)
            self._sent += to_send
            yield chunk[:to_send]

class FakeClient:
    def __init__(self) -> None:
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):  # noqa: ANN001
        return False

    def stream(self, method: str, url: str):  # type: ignore[no-untyped-def]
        class Ctx:
            def __init__(self, resp):
                self.resp = resp
            def __enter__(self):
                return self.resp
            def __exit__(self, *args):  # noqa: ANN001
                return False
        return Ctx(FakeResponse(5 * 1024))


def test_web_scraper_stream_cutoff(monkeypatch) -> None:
    tool = WebScraper()
    # Patch httpx.Client with our fake one
    monkeypatch.setattr("app.core.tools.builtins.web_scraper.httpx.Client", lambda *a, **k: FakeClient())
    res = tool.execute(url="https://example.com", max_bytes=2048)
    assert isinstance(res["text"], str)
    # Assert we did not exceed requested max_bytes by much after HTML decoding
    assert len(res["text"]) <= 4096

