"""OpenAI GPT-5 adapter for Forge 1 AI Orchestrator."""

import asyncio
import logging
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from .ai_orchestrator import LLMAdapter, TaskType
from ..logging_config import get_trace_id

logger = logging.getLogger(__name__)


class OpenAIResponse(BaseModel):
    """Standardized response from OpenAI API."""

    text: str = Field(..., description="Generated text response")
    tokens: int = Field(..., description="Number of tokens used")
    model: str = Field(..., description="Model used for generation")
    finish_reason: str = Field(..., description="Reason for completion")


class OpenAIAdapter(LLMAdapter):
    """Adapter for OpenAI GPT-5 model."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-5"):
        """Initialize OpenAI adapter.

        Args:
            api_key: OpenAI API key. If None, will try to get from OPENAI_API_KEY env var.
            model: Model name to use (default: gpt-5)
        """
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self._model = model
        self._base_url = "https://api.openai.com/v1"
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(connect=3.0, read=20.0, write=10.0, pool=3.0),
        )

        logger.info(f"Initialized OpenAI adapter for model: {self._model}")

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return f"openai-{self._model}"

    @property
    def capabilities(self) -> list[TaskType]:
        """Return supported task types."""
        return [
            TaskType.GENERAL,
            TaskType.CODE_GENERATION,
            TaskType.ANALYSIS,
            TaskType.CREATIVE,
            TaskType.REVIEW,
        ]

    async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        """Generate response from prompt using OpenAI API.

        Args:
            prompt: Input prompt for generation
            context: Additional context for the request

        Returns:
            Dict containing "text" and "tokens" keys

        Raises:
            RuntimeError: If API call fails
        """
        try:
            # Prepare the request payload
            payload = {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": context.get("max_tokens", 4000),
                "temperature": context.get("temperature", 0.7),
                "stream": False,
            }

            # Add optional parameters from context
            if "top_p" in context:
                payload["top_p"] = context["top_p"]
            if "frequency_penalty" in context:
                payload["frequency_penalty"] = context["frequency_penalty"]
            if "presence_penalty" in context:
                payload["presence_penalty"] = context["presence_penalty"]

            logger.debug(f"Sending request to OpenAI API: {self._model}")

            # Make the API call with small bounded retries and jitter
            max_retries = int(context.get("retries", 2))
            import random as _rand
            delay = 0.25 + _rand.uniform(0, 0.1)
            attempt = 0
            last_exc: Exception | None = None
            while attempt <= max_retries:
                try:
                    # Propagate trace id through headers if present
                    headers = {}
                    trace_id = get_trace_id() or str(context.get("trace_id")) if context else None
                    if trace_id:
                        headers["X-Trace-ID"] = trace_id
                    response = await self._client.post(
                        f"{self._base_url}/chat/completions",
                        json=payload,
                        headers=headers or None,
                        timeout=httpx.Timeout(connect=3.0, read=20.0),
                    )
                    break
                except httpx.RequestError as e:
                    last_exc = e
                    if attempt >= max_retries:
                        raise
                    await asyncio.sleep(delay)
                    delay = min(1.0, delay * 1.5 + _rand.uniform(0, 0.05))
                    attempt += 1

            if response.status_code != 200:
                error_msg = f"OpenAI API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Parse the response
            data = response.json()
            choice = data["choices"][0]
            message = choice["message"]

            # Extract token usage
            usage = data.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)

            result = {
                "text": message["content"],
                "tokens": total_tokens,
                "model": self._model,
                "finish_reason": choice.get("finish_reason", "unknown"),
            }

            logger.info(f"Generated response with {total_tokens} tokens")
            return result

        except httpx.RequestError as e:
            error_msg = f"Network error calling OpenAI API: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except KeyError as e:
            error_msg = f"Unexpected response format from OpenAI API: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except (ValueError, TypeError) as e:
            error_msg = f"Unexpected error in OpenAI adapter: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def close(self) -> None:
        """Close the HTTP client."""
        client = getattr(self, "_client", None)
        if client is not None:
            try:
                await client.aclose()
            except Exception:  # noqa: BLE001
                pass
            logger.info("OpenAI adapter HTTP client closed")

    def __del__(self) -> None:
        """Cleanup when adapter is destroyed."""
        try:
            # Schedule cleanup in the event loop if it exists
            loop = asyncio.get_running_loop()
            loop.create_task(self.close())
        except RuntimeError:
            # No event loop running, nothing to clean up
            pass


def create_openai_adapter(api_key: str | None = None, model: str = "gpt-5") -> OpenAIAdapter:
    """Factory function to create OpenAI adapter.

    Args:
        api_key: OpenAI API key. If None, will try to get from OPENAI_API_KEY env var.
        model: Model name to use (default: gpt-5)

    Returns:
        Configured OpenAI adapter

    Raises:
        ValueError: If API key is not available
    """
    return OpenAIAdapter(api_key=api_key, model=model)
