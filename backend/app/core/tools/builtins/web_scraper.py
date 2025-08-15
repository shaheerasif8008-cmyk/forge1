from __future__ import annotations

from typing import Any
import logging
import ipaddress
import socket
from urllib.parse import urlparse

import httpx

# Avoid importing heavy deps at module import time; import inside execute()
from ..base_tool import BaseTool
from ....policy.engine import evaluate as policy_evaluate
from ..executor import validate_egress_url
from ...config import settings
from ....exec.sandbox_manager import run_tool_sandboxed, SandboxTimeout
from ....ledger.sdk import post as ledger_post
from ...logging_config import get_trace_id
from ...telemetry.metrics_service import MetricsService
from ....db.session import SessionLocal
from ...quality.guards import check_and_reserve_tokens
from ....core.config import settings

logger = logging.getLogger(__name__)


class WebScraper(BaseTool):
    """Fetch a webpage and extract its title and visible text."""

    name = "web_scraper"
    description = "Fetch a webpage and extract visible text and title."

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        url = str(kwargs.get("url", ""))
        timeout = float(kwargs.get("timeout", 10.0))
        max_bytes = int(kwargs.get("max_bytes", 2 * 1024 * 1024))
        if not url:
            raise ValueError("url is required")
        # Egress + SSRF + HTTPS-only
        validate_egress_url(url)
        if url.startswith("http://"):
            raise ValueError("HTTP is disabled for web_scraper; use HTTPS")
        # Policy evaluation
        tenant_id = str(kwargs.get("tenant_id") or "")
        decision = policy_evaluate("tool:web_scraper", "execute", {"tenant_id": tenant_id, "url": url})
        if not decision.allow:
            raise RuntimeError(f"policy deny: {decision.reason}")
<<<<<<< Current (Your changes)
        # validate_egress_url already resolves and blocks private ranges
=======
        # SSRF guard: resolve host to ensure not private/link-local/loopback with short DNS timeout
        parsed = urlparse(url)
        host = parsed.hostname or ""
        try:
            # Add DNS timeout to prevent hanging
            socket.setdefaulttimeout(5.0)
            addr_info = socket.getaddrinfo(host, None)
            socket.setdefaulttimeout(None)  # Reset to default
        except Exception as e:  # noqa: BLE001
            socket.setdefaulttimeout(None)  # Ensure timeout is reset
            raise ValueError("Unable to resolve host for SSRF checks") from e
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
                # Block private/loopback/link-local
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    raise ValueError("Blocked private address")
                # Block IPv6 ULA (fc00::/7) - Unique Local Addresses
                if ip.version == 6:
                    if isinstance(ip, ipaddress.IPv6Address):
                        # fc00::/7 includes fc00:: to fdff:ffff:ffff:ffff:ffff:ffff:ffff:ffff
                        if ip.packed[0] & 0xfe == 0xfc:
                            raise ValueError("Blocked IPv6 ULA address")
            except ValueError:
                continue
>>>>>>> Incoming (Background Agent changes)
        # Ensure BeautifulSoup is available
        try:
            from bs4 import BeautifulSoup as _BeautifulSoup  # type: ignore
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                "beautifulsoup4 is required for web_scraper. Install with `pip install beautifulsoup4`."
            ) from e

        headers = {"User-Agent": "Forge1-WebScraper/1.0"}
        tenant_id = str(kwargs.get("tenant_id") or "")
        employee_id = str(kwargs.get("employee_id") or "") or None
        # Reserve small token-equivalent budget
        try:
            if tenant_id:
                ok = check_and_reserve_tokens(tenant_id, employee_id, 128)
                if not ok:
                    raise ValueError("Daily token budget reached")
        except Exception as e:  # noqa: BLE001
            raise
        trace_id = get_trace_id()
        if trace_id:
            headers["X-Trace-ID"] = trace_id
        if getattr(settings, "SANDBOX_ENABLED", False):
            try:
                result = run_tool_sandboxed(
                    handler_module="app.core.tools.builtins.web_scraper",
                    handler_name="_sandbox_entry",
                    payload={"url": url, "timeout": timeout, "max_bytes": max_bytes},
                    timeout_secs=int(timeout) + 2,
                )
                try:
                    with SessionLocal() as db:
                        ledger_post(
                            db,
                            tenant_id=tenant_id or None,
                            journal_name="tool_usage",
                            external_id=None,
                            lines=[
                                {"account_name": "tool_expense", "side": "debit", "commodity": "tokens", "amount": 1},
                                {"account_name": "tool_reserve", "side": "credit", "commodity": "tokens", "amount": 1},
                            ],
                        )
                except Exception:
                    pass
                return result
            except SandboxTimeout:
                raise RuntimeError("sandbox timeout")

        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            logger.info("Tool web_scraper fetching URL")
            if hasattr(client, "stream"):
                with client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    ctype = resp.headers.get("Content-Type", "").lower()
                    if "text/html" not in ctype and "application/xhtml" not in ctype:
                        raise RuntimeError("URL did not return HTML content")
                    clen = resp.headers.get("Content-Length")
                    if clen is not None:
                        try:
                            if int(clen) > max_bytes:
                                raise RuntimeError("Response too large")
                        except Exception:
                            pass
                    collected = bytearray()
                    for chunk in resp.iter_bytes():
                        if not chunk:
                            break
                        remaining = max_bytes - len(collected)
                        if remaining <= 0:
                            break
                        collected.extend(chunk[:remaining])
                        if len(collected) >= max_bytes:
                            break
                    html = bytes(collected).decode(resp.encoding or "utf-8", errors="ignore")
            else:
                resp = client.get(url)
                resp.raise_for_status()
                ctype = resp.headers.get("Content-Type", "").lower()
                if "text/html" not in ctype and "application/xhtml" not in ctype:
                    raise RuntimeError("URL did not return HTML content")
                clen = resp.headers.get("Content-Length")
                if clen is not None:
                    try:
                        if int(clen) > max_bytes:
                            raise RuntimeError("Response too large")
                    except Exception:
                        pass
                content = resp.content[: max_bytes + 1]
                if len(content) > max_bytes:
                    raise RuntimeError("Response too large")
                html = content.decode(resp.encoding or "utf-8", errors="ignore")
        soup = _BeautifulSoup(html, "html.parser")
        title = (soup.title.string if soup.title else "").strip()
        # Remove script/style
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        text = " ".join(soup.get_text(separator=" ").split())
        logger.info("Tool web_scraper parsed HTML")
        try:
            if tenant_id:
                ms = MetricsService()
                ms.incr_tool_call(tenant_id=tenant_id, employee_id=employee_id)
                try:
                    with SessionLocal() as db:
                        ms.rollup_tool_call(db, tenant_id=tenant_id, employee_id=employee_id)
                except Exception:
                    pass
        except Exception:
            pass
        # ledger nominal record
        try:
            with SessionLocal() as db:
                ledger_post(
                    db,
                    tenant_id=tenant_id or None,
                    journal_name="tool_usage",
                    external_id=None,
                    lines=[
                        {"account_name": "tool_expense", "side": "debit", "commodity": "tokens", "amount": 1},
                        {"account_name": "tool_reserve", "side": "credit", "commodity": "tokens", "amount": 1},
                    ],
                )
        except Exception:
            pass
        return {"title": title, "text": text[:10000], "length": len(text)}


TOOLS = {WebScraper.name: WebScraper()}


def _sandbox_entry(**kwargs: Any) -> dict[str, Any]:  # pragma: no cover - exercised via sandbox
    import httpx as _httpx
    from bs4 import BeautifulSoup as _BeautifulSoup  # type: ignore
    url = str(kwargs.get("url", ""))
    timeout = float(kwargs.get("timeout", 10.0))
    max_bytes = int(kwargs.get("max_bytes", 2 * 1024 * 1024))
    headers = {"User-Agent": "Forge1-WebScraper/1.0"}
    with _httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        content = resp.content[: max_bytes + 1]
        if len(content) > max_bytes:
            raise RuntimeError("Response too large")
        html = content.decode(resp.encoding or "utf-8", errors="ignore")
    soup = _BeautifulSoup(html, "html.parser")
    title = (soup.title.string if soup.title else "").strip()
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    text = " ".join(soup.get_text(separator=" ").split())
    return {"title": title, "text": text[:10000], "length": len(text)}
