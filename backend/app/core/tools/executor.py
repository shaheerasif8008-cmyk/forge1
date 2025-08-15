from __future__ import annotations

import json
import os
import socket
import ipaddress
import tempfile
import subprocess
from typing import Any, Callable


def _read_allowlist_from_env() -> list[str]:
    raw = os.getenv("ALLOWLIST_DOMAINS", "").strip()
    if not raw:
        return []
    return [d.strip().lower() for d in raw.split(",") if d.strip()]


def _read_deny_cidrs_from_env() -> list[str]:
    raw = os.getenv("DENYLIST_CIDRS", "").strip()
    if not raw:
        return []
    return [c.strip() for c in raw.split(",") if c.strip()]


def _domain_matches_allowlist(host: str, allowlist: list[str]) -> bool:
    host_l = host.lower()
    for entry in allowlist:
        entry_l = entry.lstrip(".").lower()
        if host_l == entry_l or host_l.endswith("." + entry_l):
            return True
    return False


def validate_egress_url(url: str, *, allowlist: list[str] | None = None) -> None:
    """Validate that a URL is allowed for egress.

    - Scheme must be http(s)
    - If ALLOWLIST_DOMAINS is set (or provided), host must match allowlist
    - Resolve DNS and block connections to private/loopback/link-local/ULA ranges
    - Apply optional DENYLIST_CIDRS block list
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http(s) URLs are allowed")
    host = parsed.hostname or ""
    if not host:
        raise ValueError("URL must include a hostname")
    allow = allowlist if allowlist is not None else _read_allowlist_from_env()
    if allow:
        if not _domain_matches_allowlist(host, allow):
            raise ValueError("Domain not in egress allowlist")

    deny_cidrs = []
    try:
        deny_cidrs = [ipaddress.ip_network(c) for c in _read_deny_cidrs_from_env()]
    except Exception:
        deny_cidrs = []

    # Resolve host; block private/link-local/loopback/ULA
    try:
        addr_info = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except Exception as e:  # noqa: BLE001
        raise ValueError("Unable to resolve host for egress checks") from e
    for _, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0]
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or (ip.version == 6 and ip.is_private):
            raise ValueError("Blocked private address")
        for n in deny_cidrs:
            if ip in n:
                raise ValueError("Address blocked by denylist")


class HardenedExecutor:
    """Run tool handlers in a subprocess with CPU/memory/time limits and a cwd jail.

    This executor is intentionally minimal and portable across POSIX platforms.
    """

    def __init__(
        self,
        *,
        python_exec: str | None = None,
    ) -> None:
        self._python = python_exec or os.environ.get("PYTHON", "python3")

    def run(
        self,
        *,
        handler_module: str,
        handler_name: str,
        payload: dict[str, Any],
        timeout_secs: int = 5,
        cpu_seconds: int | None = None,
        memory_bytes: int | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        code = f"""
import importlib, json, sys
mod = importlib.import_module('{handler_module}')
fn = getattr(mod, '{handler_name}')
inp = json.loads(sys.stdin.read())
out = fn(**inp)
sys.stdout.write(json.dumps(out))
"""
        # Create a temporary jail directory for cwd
        jail_dir = tempfile.mkdtemp(prefix="forge_tool_")
        # Write runner file
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py") as tf:
            tf.write(code)
            tf.flush()
            path = tf.name

        # Setup resource limits via preexec_fn (POSIX only)
        def _set_limits() -> None:  # pragma: no cover - exercised indirectly
            try:
                import resource  # type: ignore

                if cpu_seconds is not None and cpu_seconds > 0:
                    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
                if memory_bytes is not None and memory_bytes > 0:
                    # Address space limit (may not be strict on all OSes)
                    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
                # Disallow core dumps
                try:
                    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                except Exception:
                    pass
            except Exception:
                # Limits not supported on this platform
                pass

        # Construct a minimal environment
        env = {
            "PYTHONUNBUFFERED": "1",
            # Preserve PYTHONPATH to allow importing app.* from repo root
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        }
        # Pass through allow/deny configuration for egress helpers inside child
        for k in ("ALLOWLIST_DOMAINS", "DENYLIST_CIDRS"):
            if k in os.environ:
                env[k] = os.environ[k]
        if extra_env:
            env.update(extra_env)

        try:
            proc = subprocess.Popen(
                [self._python, path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=jail_dir,
                env=env,
                preexec_fn=_set_limits if os.name == "posix" else None,
                start_new_session=True,
            )
            out, err = proc.communicate(json.dumps(payload), timeout=timeout_secs)
            if proc.returncode != 0:
                raise RuntimeError("tool execution failed")
            try:
                return json.loads(out or "{}")
            except Exception as e:  # noqa: BLE001
                raise RuntimeError("invalid tool output") from e
        except subprocess.TimeoutExpired as e:
            try:
                proc.kill()
            except Exception:
                pass
            raise RuntimeError("tool timeout") from e
        except Exception:
            raise
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass


