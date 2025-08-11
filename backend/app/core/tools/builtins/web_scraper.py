from __future__ import annotations

from typing import Any

import httpx
# Avoid importing heavy deps at module import time; import inside execute()

from ..base_tool import BaseTool


class WebScraper(BaseTool):
    """Fetch a webpage and extract its title and visible text."""

    name = "web_scraper"
    description = "Fetch a webpage and extract visible text and title."

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        url = str(kwargs.get("url", ""))
        timeout = float(kwargs.get("timeout", 20.0))
        if not url:
            raise ValueError("url is required")
        # Ensure BeautifulSoup is available
        try:
            from bs4 import BeautifulSoup as _BeautifulSoup  # type: ignore
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                "beautifulsoup4 is required for web_scraper. Install with `pip install beautifulsoup4`."
            ) from e

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
        soup = _BeautifulSoup(html, "html.parser")
        title = (soup.title.string if soup.title else "").strip()
        # Remove script/style
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        text = " ".join(soup.get_text(separator=" ").split())
        return {"title": title, "text": text[:10000], "length": len(text)}


TOOLS = {WebScraper.name: WebScraper()}
