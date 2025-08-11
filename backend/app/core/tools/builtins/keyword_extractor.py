from __future__ import annotations

from typing import Any

from ...memory.encoder import MemoryEncoder
from ..base_tool import BaseTool

PROMPT = (
    "Extract 5-15 concise, relevant keywords from the text. "
    "Return them as a comma-separated list without additional text.\n\nText:\n{body}"
)


class KeywordExtractor(BaseTool):
    """Extract relevant keywords using an LLM via MemoryEncoder."""

    name = "keyword_extractor"
    description = "Extract relevant keywords from text using an LLM."

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        body = str(kwargs.get("text", "")).strip()
        if not body:
            return {"keywords": []}
        prompt = PROMPT.format(body=body[:4000])
        with MemoryEncoder() as enc:
            summary = enc.summarize(prompt, max_tokens=128)
        # Parse keywords
        parts = [p.strip() for p in summary.replace("\n", ",").split(",") if p.strip()]
        # Deduplicate while preserving order
        seen: set[str] = set()
        keywords: list[str] = []
        for p in parts:
            if p.lower() not in seen:
                keywords.append(p)
                seen.add(p.lower())
        return {"keywords": keywords[:15]}


TOOLS = {KeywordExtractor.name: KeywordExtractor()}
