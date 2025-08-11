"""Anthropic Claude 4.1 adapter for Forge 1 AI Orchestrator."""

import asyncio
import logging
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from .ai_orchestrator import LLMAdapter, TaskType

logger = logging.getLogger(__name__)


class ClaudeResponse(BaseModel):
    """Standardized response from Claude API."""

    text: str = Field(..., description="Generated text response")
    tokens: int = Field(..., description="Number of tokens used")
    model: str = Field(..., description="Model used for generation")
    stop_reason: str = Field(..., description="Reason for completion")


class ClaudeAdapter(LLMAdapter):
    """Adapter for Anthropic Claude 4.1 model."""

    def __init__(self, api_key: str | None = None, model: str = "claude-4-1-sonnet-20241022"):
        """Initialize Claude adapter.

        Args:
            api_key: Anthropic API key. If None, will try to get from ANTHROPIC_API_KEY env var.
            model: Model name to use (default: claude-4-1-sonnet-20241022)
        """
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ValueError(
                "Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self._model = model
        self._base_url = "https://api.anthropic.com/v1"
        self._client = httpx.AsyncClient(
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

        logger.info(f"Initialized Claude adapter for model: {self._model}")

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return f"claude-{self._model}"

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
        """Generate response from prompt using Claude API.

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
                "max_tokens": context.get("max_tokens", 4000),
                "temperature": context.get("temperature", 0.7),
                "system": context.get("system_prompt", "You are a helpful AI assistant."),
                "messages": [{"role": "user", "content": prompt}],
            }

            # Add optional parameters from context
            if "top_p" in context:
                payload["top_p"] = context["top_p"]
            if "top_k" in context:
                payload["top_k"] = context["top_k"]

            logger.debug(f"Sending request to Claude API: {self._model}")

            # Make the API call
            response = await self._client.post(
                f"{self._base_url}/messages",
                json=payload,
            )

            if response.status_code != 200:
                error_msg = f"Claude API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Parse the response
            data = response.json()
            content = data["content"][0]

            # Extract token usage
            usage = data.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            total_tokens = input_tokens + output_tokens

            result = {
                "text": content["text"],
                "tokens": total_tokens,
                "model": self._model,
                "stop_reason": data.get("stop_reason", "unknown"),
            }

            logger.info(
                f"Generated response with {total_tokens} tokens (input: {input_tokens}, output: {output_tokens})"
            )
            return result

        except httpx.RequestError as e:
            error_msg = f"Network error calling Claude API: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except KeyError as e:
            error_msg = f"Unexpected response format from Claude API: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except (ValueError, TypeError) as e:
            error_msg = f"Unexpected error in Claude adapter: {str(e)}"
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
            logger.info("Claude adapter HTTP client closed")

    def __del__(self) -> None:
        """Cleanup when adapter is destroyed."""
        try:
            # Schedule cleanup in the event loop if it exists
            loop = asyncio.get_running_loop()
            loop.create_task(self.close())
        except RuntimeError:
            # No event loop running, nothing to clean up
            pass


def create_claude_adapter(
    api_key: str | None = None, model: str = "claude-4-1-sonnet-20241022"
) -> ClaudeAdapter:
    """Factory function to create Claude adapter.

    Args:
        api_key: Anthropic API key. If None, will try to get from ANTHROPIC_API_KEY env var.
        model: Model name to use (default: claude-4-1-sonnet-20241022)

    Returns:
        Configured Claude adapter

    Raises:
        ValueError: If API key is not available
    """
    return ClaudeAdapter(api_key=api_key, model=model)
