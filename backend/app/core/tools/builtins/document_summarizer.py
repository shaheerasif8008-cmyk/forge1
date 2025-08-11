from __future__ import annotations

from typing import Any

from ...memory.encoder import MemoryEncoder
from ..base_tool import BaseTool


class DocumentSummarizer(BaseTool):
    """Summarize long text with an LLM via MemoryEncoder."""

    name = "doc_summarizer"
    description = "Summarize text using an LLM."

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        text = str(kwargs.get("text", ""))
        max_tokens = int(kwargs.get("max_tokens", 300))
        if not text.strip():
            return {"summary": ""}
        with MemoryEncoder() as enc:
            summary = enc.summarize(text, max_tokens=max_tokens)
        return {"summary": summary}


TOOLS = {DocumentSummarizer.name: DocumentSummarizer()}
