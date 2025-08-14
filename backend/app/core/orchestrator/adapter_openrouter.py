"""OpenRouter adapter for Forge 1.

Uses a single OPENROUTER_API_KEY for routing to multiple model providers.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Final

import httpx
from pydantic import BaseModel, Field

from .ai_orchestrator import LLMAdapter, TaskType
from ..config import settings
from ..quality.guards import clamp_tokens, check_and_reserve_tokens
from ..logging_config import get_trace_id

logger = logging.getLogger(__name__)


class OpenRouterResponse(BaseModel):
    text: str = Field(...)
    tokens: int = Field(default=0)
    model: str = Field(...)
    finish_reason: str = Field(default="stop")


MODEL_MAP: Final[dict[str, str]] = {
    # Common aliases mapped to OpenRouter model IDs (can be extended via config if needed)
    "gpt-4o": "openai/gpt-4o",
    "gpt-4": "openai/gpt-4",
    "gpt-3.5": "openai/gpt-3.5-turbo",
    "claude-3.5": "anthropic/claude-3.5-sonnet",
    "claude-3-opus": "anthropic/claude-3-opus",
    "gemini-1.5": "google/gemini-1.5-pro",
    "mistral-medium": "mistralai/mistral-medium",
}


class OpenRouterAdapter(LLMAdapter):
    def __init__(self, api_key: str | None = None, default_model: str = "gpt-4o"):
        self._api_key = api_key or settings.openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        if not self._api_key:
            raise ValueError("OPENROUTER_API_KEY is required for OpenRouterAdapter")
        self._base_url = "https://openrouter.ai/api/v1"
        self._default_model = default_model
        timeout = float(getattr(settings, "llm_timeout_secs", 45.0))
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
        logger.info("Initialized OpenRouter adapter")

    @property
    def model_name(self) -> str:  # synthetic name
        return f"openrouter-{self._default_model}"

    @property
    def capabilities(self) -> list[TaskType]:
        return [
            TaskType.GENERAL,
            TaskType.CODE_GENERATION,
            TaskType.ANALYSIS,
            TaskType.CREATIVE,
            TaskType.REVIEW,
        ]

    def _resolve_model(self, requested: str | None) -> str:
        if requested and requested in MODEL_MAP:
            return MODEL_MAP[requested]
        # Allow passing a fully-qualified OpenRouter model id directly
        if requested and "/" in requested:
            return requested
        return MODEL_MAP.get(self._default_model, self._default_model)

    async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        try:
            requested_model = str(context.get("model_name", "") or self._default_model)
            model = self._resolve_model(requested_model)
            requested_max = int(context.get("max_tokens", getattr(settings, "max_tokens_per_req", 2048)))
            max_tokens = clamp_tokens(requested_max)
            # Reserve tokens against per-employee daily budget
            employee_id = str(context.get("employee_id", "") or "") or None
            if not check_and_reserve_tokens(employee_id, max_tokens):
                raise RuntimeError("Daily token budget reached for employee")
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": context.get("temperature", 0.7),
                "stream": False,
            }

            # Optional params
            for key_src, key_dst in (("top_p", "top_p"), ("frequency_penalty", "frequency_penalty"), ("presence_penalty", "presence_penalty")):
                if key_src in context:
                    payload[key_dst] = context[key_src]

            headers: dict[str, str] = {}
            trace_id = get_trace_id() or str(context.get("trace_id")) if context else None
            if trace_id:
                headers["X-Trace-ID"] = trace_id

            logger.debug(f"Sending request to OpenRouter: {model}")
            max_retries = int(context.get("retries", 1))
            attempt = 0
            last_exc: Exception | None = None
            # Simple circuit breaker per model route (in-memory/redis)
            brk_key = f"cb:openrouter:{model}"
            r = None
            try:
                from redis import Redis as _R

                r = _R.from_url(settings.redis_url, decode_responses=True)
                state = r.get(brk_key)
                if state == "open":
                    raise RuntimeError("Circuit breaker open for model")
            except Exception:
                pass

            failure_count = 0
            cooldown = 15

            while attempt <= max_retries:
                try:
                    response = await self._client.post(
                        f"{self._base_url}/chat/completions",
                        json=payload,
                        headers=headers or None,
                    )
                    break
                except httpx.RequestError as e:  # type: ignore[name-defined]
                    last_exc = e
                    failure_count += 1
                    if attempt >= max_retries:
                        # Trip breaker
                        try:
                            if r is not None:
                                r.setex(brk_key, cooldown, "open")
                        except Exception:
                            pass
                        raise
                    await asyncio.sleep(0.3)
                    attempt += 1

            if response.status_code != 200:
                raise RuntimeError(f"OpenRouter error: {response.status_code} - {response.text}")

            data = response.json()
            choice = data["choices"][0]
            message = choice["message"]
            usage = data.get("usage", {})
            total_tokens = int(usage.get("total_tokens", 0))
            result = {
                "text": message["content"],
                "tokens": total_tokens,
                "model": model,
                "finish_reason": choice.get("finish_reason", "unknown"),
            }
            logger.info(f"OpenRouter response tokens={total_tokens} model={model}")
            return result
        except Exception as e:  # noqa: BLE001
            logger.error(f"OpenRouter generate failed: {e}")
            raise


