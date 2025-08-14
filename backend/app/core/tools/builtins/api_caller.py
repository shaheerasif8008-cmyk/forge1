from __future__ import annotations

from typing import Any
import logging
import random
import time
import ipaddress
import socket
from urllib.parse import urlparse

import httpx
import json as _json

from ..base_tool import BaseTool
from ....policy.engine import evaluate as policy_evaluate
from ....exec.sandbox_manager import run_tool_sandboxed, SandboxTimeout
from ....ledger.sdk import post as ledger_post
from ...logging_config import get_trace_id
from ...telemetry.metrics_service import MetricsService
from ....db.session import SessionLocal
from ...quality.guards import check_and_reserve_tokens
from ....core.config import settings

logger = logging.getLogger(__name__)


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
        timeout = float(kwargs.get("timeout", 10.0))
        retries = int(kwargs.get("retries", 2))
        allow_http = bool(kwargs.get("allow_http", False))
        max_bytes = int(kwargs.get("max_bytes", 2 * 1024 * 1024))
        content_whitelist = {"application/json", "text/plain", "text/csv"}

        # optional context for metrics
        tenant_id = str(kwargs.get("tenant_id") or "")
        employee_id = str(kwargs.get("employee_id") or "") or None

        method_norm = method.upper().strip()
        # Policy evaluation
        decision = policy_evaluate("tool:api_caller", "execute", {"tenant_id": tenant_id, "url": url, "method": method_norm})
        if not decision.allow:
            raise RuntimeError(f"policy deny: {decision.reason}")
        if not url:
            raise ValueError("url is required")

        # Scheme allowlist; prefer HTTPS; optionally allow HTTP only if explicitly enabled.
        if url.startswith("http://") and not allow_http:
            raise ValueError("HTTP is disabled. Set allow_http=true to permit.")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("Only http(s) URLs are allowed")
        # SSRF guard: resolve host and block private/link-local/loopback/IPv6 ULA
        try:
            parsed = urlparse(url)
            host = parsed.hostname or ""
            # Add DNS timeout to prevent hanging
            socket.setdefaulttimeout(5.0)
            addr_info = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
            socket.setdefaulttimeout(None)  # Reset to default
            for _, _, _, _, sockaddr in addr_info:
                ip_str = sockaddr[0]
                ip = ipaddress.ip_address(ip_str)
                # Block private/link-local/loopback
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    raise ValueError("Blocked private address")
                # Block IPv6 ULA (fc00::/7) - Unique Local Addresses
                if ip.version == 6:
                    # Check if it's in fc00::/7 range
                    if isinstance(ip, ipaddress.IPv6Address):
                        # fc00::/7 includes fc00:: to fdff:ffff:ffff:ffff:ffff:ffff:ffff:ffff
                        if ip.packed[0] & 0xfe == 0xfc:
                            raise ValueError("Blocked IPv6 ULA address")
        except ValueError as e:
            # Re-raise our own ValueError messages
            raise e
        except Exception as e:  # noqa: BLE001
            # Normalize error to avoid leaking host resolution details
            raise ValueError("Unable to resolve host for SSRF checks") from e
        finally:
            socket.setdefaulttimeout(None)  # Ensure timeout is reset
        base_headers = {"User-Agent": "Forge1-APICaller/1.0"}
        merged_headers = {**base_headers, **(headers or {})}

        def _should_retry(status_code: int | None, err: Exception | None) -> bool:
            if err is not None:
                return True
            if status_code is None:
                return False
            return 500 <= status_code < 600

        # propagate trace id in headers if present
        trace_id = get_trace_id()
        if trace_id:
            merged_headers["X-Trace-ID"] = trace_id
        # Reserve a nominal token-equivalent budget for tool calls (approximate)
        try:
            if tenant_id:
                # treat response size cap as token proxy
                budget_ok = check_and_reserve_tokens(tenant_id, employee_id, 128)
                if not budget_ok:
                    raise ValueError("Daily token budget reached")
        except Exception as e:
            logger.error("Tool api_caller budget check failed", exc_info=e)
            raise

        # Sandbox when enabled
        if getattr(settings, "SANDBOX_ENABLED", False):
            try:
                result = run_tool_sandboxed(
                    handler_module="app.core.tools.builtins.api_caller",
                    handler_name="_sandbox_entry",
                    payload={
                        "method": method_norm,
                        "url": url,
                        "headers": merged_headers,
                        "params": params,
                        "json_body": json_body,
                        "timeout": timeout,
                        "retries": retries,
                        "allow_http": allow_http,
                        "max_bytes": max_bytes,
                    },
                    timeout_secs=int(timeout) + 2,
                )
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
                return result
            except SandboxTimeout:
                raise RuntimeError("sandbox timeout")

        with httpx.Client(timeout=timeout, follow_redirects=True, headers=merged_headers) as client:
            attempt = 0
            last_exc: Exception | None = None
            while attempt <= retries:
                try:
                    logger.info(
                        f"Tool api_caller request attempt {attempt+1}",
                    )
                    resp = client.request(method_norm, url, params=params, json=json_body)
                    if _should_retry(resp.status_code, None) and attempt < retries:
                        # small jittered backoff
                        time.sleep(0.2 * (attempt + 1) + random.uniform(0, 0.1))
                        attempt += 1
                        continue
                    resp.raise_for_status()
                    # Enforce content-type whitelist and size cap
                    ctype = (resp.headers.get("Content-Type") or "").split(";")[0].lower().strip()
                    if ctype and ctype not in content_whitelist:
                        raise RuntimeError("Disallowed content-type")
                    content = resp.content[: max_bytes + 1]
                    if len(content) > max_bytes:
                        raise RuntimeError("Response too large (cap 2MB).")
                    try:
                        data = resp.json()
                    except Exception:  # noqa: BLE001
                        data = {"text": content.decode(resp.encoding or "utf-8", errors="ignore")}
                    logger.info(
                        f"Tool api_caller response {resp.status_code}",
                    )
                    # Metrics: count tool call
                    try:
                        if tenant_id:
                            ms = MetricsService()
                            ms.incr_tool_call(tenant_id=tenant_id, employee_id=employee_id)
                            # Persist daily rollup to DB
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
                    return {"status_code": resp.status_code, "headers": dict(resp.headers), "data": data}
                except httpx.RequestError as e:  # network error
                    last_exc = e
                    if attempt >= retries:
                        logger.error("Tool api_caller network error", exc_info=e)
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
                        raise
                    time.sleep(0.2 * (attempt + 1) + random.uniform(0, 0.1))
                    attempt += 1
            # If loop exits unexpectedly
            if last_exc:
                raise last_exc
            raise RuntimeError("APICaller failed without exception")


TOOLS = {APICaller.name: APICaller()}


def _sandbox_entry(**kwargs: Any) -> dict[str, Any]:  # pragma: no cover - exercised via sandbox
    # Minimal runner using same logic but without policy/ledger hooks (checked in parent)
    method = str(kwargs.get("method", "GET")).upper()
    url = str(kwargs.get("url", ""))
    headers = kwargs.get("headers") or {}
    params = kwargs.get("params")
    json_body = kwargs.get("json_body")
    timeout = float(kwargs.get("timeout", 10.0))
    retries = int(kwargs.get("retries", 1))
    allow_http = bool(kwargs.get("allow_http", False))
    max_bytes = int(kwargs.get("max_bytes", 2 * 1024 * 1024))
    if url.startswith("http://") and not allow_http:
        raise ValueError("HTTP disabled")
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("Only http(s) URLs allowed")
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        attempt = 0
        while attempt <= retries:
            try:
                resp = client.request(method, url, params=params, json=json_body)
                resp.raise_for_status()
                content = resp.content[: max_bytes + 1]
                if len(content) > max_bytes:
                    raise RuntimeError("Response too large")
                try:
                    data = resp.json()
                except Exception:
                    data = {"text": content.decode(resp.encoding or "utf-8", errors="ignore")}
                return {"status_code": resp.status_code, "headers": dict(resp.headers), "data": data}
            except Exception:
                if attempt >= retries:
                    raise
                attempt += 1
