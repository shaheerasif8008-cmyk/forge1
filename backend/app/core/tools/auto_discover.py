"""Auto-discovery for built-in tools without importing heavy deps upfront.

Scans the builtins package and imports each module via pkgutil. Built-in tools
should keep heavy dependencies inside execute() to avoid import-time failures.
"""

from __future__ import annotations

import importlib
import pkgutil


def auto_discover() -> list[str]:
    """Discover and import built-in tool modules.

    Returns list of discovered module names.
    """
    discovered: list[str] = []
    base_pkg = "app.core.tools.builtins"
    try:
        pkg = importlib.import_module(base_pkg)
        for m in pkgutil.iter_modules(pkg.__path__, prefix=f"{base_pkg}."):
            try:
                importlib.import_module(m.name)
                discovered.append(m.name)
            except (ImportError, RuntimeError):
                # Ignore failures; execute() will provide actionable errors
                continue
    except (ImportError, RuntimeError):
        return []
    return discovered
