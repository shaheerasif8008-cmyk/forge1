from __future__ import annotations

from typing import Any

import pytest

from app.core.tools.tool_registry import ToolRegistry


class EchoTool:
    def __init__(self, tool_name: str = "echo") -> None:
        self._name = tool_name

    @property
    def name(self) -> str:  # type: ignore[override]
        return self._name

    def run(self, **kwargs: Any) -> Any:  # type: ignore[override]
        return kwargs


def test_register_and_get_tool():
    reg = ToolRegistry()
    tool = EchoTool()
    reg.register(tool)

    assert reg.get("echo") is tool
    assert reg.list_tools() == ["echo"]


def test_register_duplicate_raises():
    reg = ToolRegistry()
    reg.register(EchoTool("alpha"))
    with pytest.raises(ValueError):
        reg.register(EchoTool("alpha"))


def test_load_builtins_gracefully_handles_absent_package(monkeypatch):
    reg = ToolRegistry()
    # Temporarily point builtins module to a non-existent one by monkeypatching import_module
    import importlib

    original_import = importlib.import_module

    def fake_import(name: str):  # type: ignore[no-redef]
        if name == "app.core.tools.builtins":
            raise ImportError("no builtins")
        return original_import(name)

    monkeypatch.setattr(importlib, "import_module", fake_import)

    res = reg.load_builtins()
    assert res.modules_loaded == 0
    assert res.tools_registered == 0
