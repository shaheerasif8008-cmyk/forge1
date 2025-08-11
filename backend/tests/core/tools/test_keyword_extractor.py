from __future__ import annotations

from typing import Any

import app.core.tools.builtins.keyword_extractor as mod


def test_keyword_extractor_mock(monkeypatch):
    class DummyEncoder:
        def __enter__(self) -> DummyEncoder:  # noqa: D401
            return self

        def __exit__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
            return None

        def summarize(self, content: str, max_tokens: int = 128) -> str:  # noqa: D401
            return "alpha, beta, beta, gamma"

    monkeypatch.setattr(mod, "MemoryEncoder", DummyEncoder)
    tool = mod.KeywordExtractor()
    out = tool.execute(text="hello world")
    assert out["keywords"] == ["alpha", "beta", "gamma"]
