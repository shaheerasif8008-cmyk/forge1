"""Tool registry for managing built-in and custom tools.

The registry stores tools by name and can dynamically load built-ins from
`app.core.tools.builtins`.

Tool interface (structural typing via Protocol):
    - property `name: str`
    - method `run(**kwargs) -> Any`

Modules under `app.core.tools.builtins` should export either:
    - TOOLS: dict[str, Tool]
    - or a function get_tools() -> dict[str, Tool]
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class Tool(Protocol):
    """Protocol for tools usable by the platform."""

    @property
    def name(self) -> str:  # pragma: no cover - trivial accessors
        ...

    def run(self, **kwargs: Any) -> Any:  # pragma: no cover - implemented by tools
        ...


@dataclass
class LoadResult:
    """Result of a built-in load operation."""

    modules_loaded: int
    tools_registered: int


class ToolRegistry:
    """Registry for registering and retrieving tools by name."""

    def __init__(self) -> None:
        self._name_to_tool: dict[str, Tool] = {}
        # Auto discover built-ins on init for convenience
        try:
            from .auto_discover import auto_discover

            auto_discover()
        except (ImportError, RuntimeError):
            # Non-fatal; explicit load_builtins() can still be used
            pass

    # Core operations
    def register(self, tool: Tool, *, override: bool = False) -> None:
        """Register a tool.

        Args:
            tool: Tool instance implementing the Tool protocol
            override: If True, replace any existing tool with the same name
        """
        tool_name = tool.name.strip()
        if not tool_name:
            raise ValueError("Tool must have a non-empty name")
        if not override and tool_name in self._name_to_tool:
            raise ValueError(f"Tool '{tool_name}' is already registered")
        self._name_to_tool[tool_name] = tool

    def get(self, name: str) -> Tool | None:
        """Retrieve a tool by name."""
        return self._name_to_tool.get(name)

    def list_tools(self) -> list[str]:
        """List registered tool names, sorted alphabetically."""
        return sorted(self._name_to_tool.keys())

    # Built-ins loading
    def load_builtins(self) -> LoadResult:
        """Load built-in tools from the builtins package.

        Returns:
            LoadResult with counts of modules loaded and tools registered.
        """
        # Compute filesystem path for builtins
        base_pkg = "app.core.tools.builtins"
        try:
            pkg = importlib.import_module(base_pkg)
            pkg_path = Path(inspect.getfile(pkg)).parent
        except Exception:  # noqa: BLE001
            # Builtins not present is not a fatal error
            return LoadResult(modules_loaded=0, tools_registered=0)

        modules_loaded = 0
        tools_registered = 0

        for file in pkg_path.glob("*.py"):
            if file.name.startswith("__"):
                continue
            module_name = file.stem
            fqmn = f"{base_pkg}.{module_name}"
            try:
                mod = importlib.import_module(fqmn)
                modules_loaded += 1

                tools_dict: dict[str, Tool] | None = None
                if hasattr(mod, "TOOLS"):
                    maybe = mod.TOOLS
                    if isinstance(maybe, dict):
                        tools_dict = maybe
                if tools_dict is None and hasattr(mod, "get_tools") and callable(mod.get_tools):
                    tools_dict = mod.get_tools()

                if tools_dict:
                    for _tool_name, tool in tools_dict.items():
                        # Prefer the tool's internal name for registration
                        self.register(tool, override=True)
                        tools_registered += 1
                        import logging

                        logging.getLogger(__name__).info(f"Registered built-in tool: {tool.name}")
            except Exception:  # noqa: BLE001
                # Skip faulty modules silently to avoid breaking startup
                continue

        return LoadResult(modules_loaded=modules_loaded, tools_registered=tools_registered)
