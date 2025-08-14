"""Structured logging configuration and request context utilities.

This module configures JSON logging and provides request-scoped context
using contextvars so we can correlate logs across API, orchestration,
RAG, tools, and runtime layers.

Fields included in every log entry:
- timestamp: ISO-8601 UTC
- level: log level name
- logger: logger name
- message: formatted message
- trace_id: request/operation scoped correlation ID
- tenant_id: tenant identifier when available
- user_id: user identifier when available
- request_method: HTTP method when in a request
- request_path: HTTP path when in a request
- module, function, line: source location
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any


# Context variables for request-scoped metadata
trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
request_method_var: ContextVar[str | None] = ContextVar("request_method", default=None)
request_path_var: ContextVar[str | None] = ContextVar("request_path", default=None)


def generate_trace_id() -> str:
    """Generate a new opaque trace identifier."""
    return uuid.uuid4().hex


def set_request_context(
    *,
    trace_id: str | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
    method: str | None = None,
    path: str | None = None,
) -> None:
    """Set request-scoped logging context values.

    Any ``None`` value is ignored (keeps prior value).
    """

    if trace_id is not None:
        trace_id_var.set(trace_id)
    if tenant_id is not None:
        tenant_id_var.set(tenant_id)
    if user_id is not None:
        user_id_var.set(user_id)
    if method is not None:
        request_method_var.set(method)
    if path is not None:
        request_path_var.set(path)


def clear_request_context() -> None:
    """Clear request-scoped context values."""

    trace_id_var.set(None)
    tenant_id_var.set(None)
    user_id_var.set(None)
    request_method_var.set(None)
    request_path_var.set(None)


def get_trace_id() -> str | None:
    return trace_id_var.get()


def get_tenant_id() -> str | None:
    return tenant_id_var.get()


def get_user_id() -> str | None:
    return user_id_var.get()


class ContextFilter(logging.Filter):
    """Inject contextvars into LogRecord attributes."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401 - pydocstyle noise
        # Correlation fields
        setattr(record, "trace_id", get_trace_id() or "")
        setattr(record, "tenant_id", get_tenant_id() or "")
        setattr(record, "user_id", get_user_id() or "")

        # Request fields
        setattr(record, "request_method", request_method_var.get() or "")
        setattr(record, "request_path", request_path_var.get() or "")

        # Static app tag for queries in log platforms
        setattr(record, "app", "forge1-backend")
        return True


class JsonFormatter(logging.Formatter):
    """Render log records as JSON lines for ingestion by log platforms."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - pydocstyle noise
        # Base payload
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            # Injected by ContextFilter
            "trace_id": getattr(record, "trace_id", ""),
            "tenant_id": getattr(record, "tenant_id", ""),
            "user_id": getattr(record, "user_id", ""),
            "request_method": getattr(record, "request_method", ""),
            "request_path": getattr(record, "request_path", ""),
            "app": getattr(record, "app", "forge1-backend"),
        }

        # Exception info if present
        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload["exc_message"] = str(record.exc_info[1]) if record.exc_info[1] else None
            try:
                payload["exc_stack"] = self.formatException(record.exc_info)
            except Exception:  # noqa: BLE001
                payload["exc_stack"] = None

        return json.dumps(payload, ensure_ascii=False)


@contextmanager
def use_request_context(
    *,
    trace_id: str | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
    method: str | None = None,
    path: str | None = None,
):
    """Context manager to temporarily set request-scoped context.

    Restores previous ContextVar values on exit.
    """
    tokens: list[tuple[ContextVar[Any], Any]] = []
    try:
        if trace_id is not None:
            tokens.append((trace_id_var, trace_id_var.set(trace_id)))
        if tenant_id is not None:
            tokens.append((tenant_id_var, tenant_id_var.set(tenant_id)))
        if user_id is not None:
            tokens.append((user_id_var, user_id_var.set(user_id)))
        if method is not None:
            tokens.append((request_method_var, request_method_var.set(method)))
        if path is not None:
            tokens.append((request_path_var, request_path_var.set(path)))
        yield
    finally:
        # Reset in reverse order
        for var, token in reversed(tokens):
            try:
                var.reset(token)
            except Exception:  # noqa: BLE001
                pass


def _level_name_to_value(name: str) -> int:
    name_upper = (name or "INFO").upper()
    return {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }.get(name_upper, logging.INFO)


def configure_logging() -> None:
    """Configure root and framework loggers for JSON output.

    This function is idempotent and safe to call multiple times.
    """

    try:
        # Import lazily to avoid circulars at module import time
        from .config import settings  # local import
    except Exception:  # noqa: BLE001
        class _S:  # minimal fallback
            log_level = "INFO"

        settings = _S()  # type: ignore[assignment]

    root = logging.getLogger()
    level_value = _level_name_to_value(getattr(settings, "log_level", "INFO"))
    root.setLevel(level_value)

    # Clear existing non-null handlers to avoid duplicate logs
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(level_value)
    handler.addFilter(ContextFilter())
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    # Align common third-party loggers
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        lg = logging.getLogger(name)
        lg.setLevel(level_value)
        lg.propagate = True
        # Remove their own handlers so they bubble to root
        for h in list(lg.handlers):
            lg.removeHandler(h)


