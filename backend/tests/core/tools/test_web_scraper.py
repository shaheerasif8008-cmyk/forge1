from __future__ import annotations

import httpx

from app.core.tools.builtins.web_scraper import WebScraper
import builtins


def test_web_scraper_extracts(monkeypatch):
    tool = WebScraper()

    class DummyResponse:
        status_code = 200
        headers = {"Content-Type": "text/html; charset=utf-8", "Content-Length": "120"}
        encoding = "utf-8"

        def raise_for_status(self) -> None:  # noqa: D401
            return

        @property
        def text(self) -> str:
            return "<html><head><title>T</title></head><body><p>hi</p></body></html>"

        @property
        def content(self) -> bytes:
            return self.text.encode("utf-8")

    class DummyClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN001
            pass

        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *args, **kwargs):  # noqa: ANN001, ANN204
            return None

        def get(self, url):  # noqa: ANN001
            return DummyResponse()

    # Ensure bs4 import resolves to a dummy BeautifulSoup
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):  # noqa: ANN001
        if name == "bs4":
            class BSMod:  # noqa: D401
                class BeautifulSoup:  # noqa: D401
                    def __init__(self, html: str, parser: str) -> None:  # noqa: D401
                        self._html = html

                    @property
                    def title(self):  # noqa: D401
                        class T:  # noqa: D401
                            string = "T"

                        return T()

                    def __call__(self, tags):  # noqa: D401
                        return []

                    def get_text(self, separator: str = " ") -> str:  # noqa: D401
                        return "hi"

            return BSMod()
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(httpx, "Client", DummyClient)
    out = tool.execute(url="https://example.com")
    assert out["title"] == "T"
    assert out["length"] >= 2


def test_web_scraper_blocks_non_html(monkeypatch):
    tool = WebScraper()

    class DummyResponse:
        status_code = 200
        headers = {"Content-Type": "application/octet-stream", "Content-Length": "10"}

        def raise_for_status(self) -> None:  # noqa: D401
            return

        @property
        def text(self) -> str:
            return "binary"

    class DummyClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN001
            pass

        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *args, **kwargs):  # noqa: ANN001, ANN204
            return None

        def get(self, url):  # noqa: ANN001
            return DummyResponse()

    monkeypatch.setattr(httpx, "Client", DummyClient)
    try:
        tool.execute(url="https://example.com")
        assert False, "expected RuntimeError for content-type"
    except RuntimeError:
        pass
