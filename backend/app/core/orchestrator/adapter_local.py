from __future__ import annotations

from typing import Any

import httpx

from .ai_orchestrator import LLMAdapter, TaskType


class ForgeLocalAdapter(LLMAdapter):
    """OpenAI-compatible local inference adapter (Forge 1 Local Model).

    Requires env:
      FORGE_LOCAL_API_BASE, FORGE_LOCAL_API_KEY, optional FORGE_LOCAL_MODEL
    """

    def __init__(self) -> None:
        import os
        base = os.getenv("FORGE_LOCAL_API_BASE")
        key = os.getenv("FORGE_LOCAL_API_KEY")
        if not base or not key:
            raise RuntimeError("Forge local model not configured")
        self._base = base.rstrip("/")
        self._key = key
        self._model = os.getenv("FORGE_LOCAL_MODEL", "forge-llama-3-8b-q4")

    @property
    def model_name(self) -> str:
        return f"openai-{self._model}"

    @property
    def capabilities(self) -> list[TaskType]:
        return [TaskType.GENERAL, TaskType.ANALYSIS, TaskType.REVIEW, TaskType.CODE_GENERATION]

    async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        body = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(context.get("temperature", 0.2) or 0.2),
            "max_tokens": int(context.get("max_tokens", 512) or 512),
        }
        async with httpx.AsyncClient(base_url=self._base, timeout=30.0) as client:
            r = await client.post("/v1/chat/completions", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            tokens = int(usage.get("total_tokens", 0))
            return {"text": text, "tokens": tokens}


