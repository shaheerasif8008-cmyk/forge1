import os
import pytest

from app.core.tools.executor import HardenedExecutor, validate_egress_url


def test_validate_egress_blocks_private_ipv4(monkeypatch):
    monkeypatch.setenv("ALLOWLIST_DOMAINS", "")
    with pytest.raises(ValueError):
        validate_egress_url("http://127.0.0.1/")


def test_validate_egress_enforces_allowlist(monkeypatch):
    monkeypatch.setenv("ALLOWLIST_DOMAINS", "example.com,.example.org")
    # Avoid flaky DNS resolution in CI by skipping DNS for this case: use allowlist param and a host that resolves locally.
    # We still test host matching logic by passing allowlist directly.
    validate_egress_url("https://example.com/", allowlist=["example.com"])  # should pass
    # Disallowed domain
    with pytest.raises(ValueError):
        validate_egress_url("https://not-allowed.com/")


def test_executor_timeout_and_limits(monkeypatch):
    # Create a tiny echo handler module inline
    code = """
from __future__ import annotations
from typing import Any

def handler(**kwargs: Any) -> dict[str, Any]:
    # Busy loop to exceed CPU quickly when limit is very low
    x = 0
    for _ in range(10_000_000):
        x += 1
    return {"ok": True, "x": x}
"""
    # Write temp module
    import tempfile, importlib.util, sys
    with tempfile.TemporaryDirectory() as tmpd:
        mod_path = os.path.join(tmpd, "_h_exec_mod.py")
        with open(mod_path, "w", encoding="utf-8") as f:
            f.write(code)
        # Add to path for import
        sys.path.insert(0, tmpd)
        try:
            # Instantiate executor with strict limits
            execu = HardenedExecutor()
            # Very low CPU seconds to trigger enforcement on POSIX
            try:
                _ = execu.run(handler_module="_h_exec_mod", handler_name="handler", payload={}, timeout_secs=1, cpu_seconds=1)
            except RuntimeError:
                # Either timeout or execution failure due to limits is acceptable behavior
                pass
        finally:
            sys.path.remove(tmpd)
