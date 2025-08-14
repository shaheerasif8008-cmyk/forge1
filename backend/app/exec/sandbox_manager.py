from __future__ import annotations

import json
import os
import subprocess
import tempfile
from typing import Any

from ..core.config import settings


class SandboxTimeout(Exception):
    pass


def run_tool_sandboxed(handler_module: str, handler_name: str, payload: dict[str, Any], *, timeout_secs: int = 5) -> dict[str, Any]:
    """Execute a tool handler in a minimal subprocess with resource limits.

    For portability in tests, we use a subprocess of the same Python, not Docker.
    JSON passed on stdin, result JSON on stdout.
    """
    py = os.environ.get("PYTHON", "python3")
    code = f"""
import importlib, json, sys
mod = importlib.import_module('{handler_module}')
fn = getattr(mod, '{handler_name}')
inp = json.loads(sys.stdin.read())
out = fn(**inp)
sys.stdout.write(json.dumps(out))
"""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py") as tf:
        tf.write(code)
        tf.flush()
        path = tf.name
    try:
        proc = subprocess.Popen([py, path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = proc.communicate(json.dumps(payload), timeout=timeout_secs)
        if proc.returncode != 0:
            raise RuntimeError(f"sandboxed handler error: {err}")
        return json.loads(out or "{}")
    except subprocess.TimeoutExpired as e:
        proc.kill()
        raise SandboxTimeout("tool execution timed out") from e
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


