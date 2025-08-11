"""Base tool interface for the Forge 1 tool system.

All tools should inherit from `BaseTool` and implement `execute(**kwargs)`.
The `run(**kwargs)` method is provided for compatibility with the registry's
tool protocol and delegates to `execute`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base class for tools.

    Attributes:
        name: Unique, stable name of the tool
        description: Human-readable description of what the tool does
    """

    name: str
    description: str

    def run(self, **kwargs: Any) -> Any:
        """Invoke the tool.

        This delegates to `execute` for compatibility with the ToolRegistry.
        """
        return self.execute(**kwargs)

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:  # pragma: no cover - enforced by subclasses
        """Execute the tool with keyword arguments supplied by the caller."""
        raise NotImplementedError
