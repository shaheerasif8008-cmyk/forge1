from __future__ import annotations

from typing import Any

import app.core.tools.builtins.document_summarizer as mod


def test_document_summarizer_mock(monkeypatch):
    class DummyEncoder:
        def __enter__(self) -> DummyEncoder:  # noqa: D401
            return self

        def __exit__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
            return None

        def summarize(self, content: str, max_tokens: int = 300) -> str:  # noqa: D401
            return "summary"

    monkeypatch.setattr(mod, "MemoryEncoder", DummyEncoder)
    tool = mod.DocumentSummarizer()
    out = tool.execute(text="hello")
    assert out["summary"] == "summary"
