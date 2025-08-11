"""Google Gemini 1.5 Pro adapter for Forge 1 AI Orchestrator."""

import asyncio
import logging
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from .ai_orchestrator import LLMAdapter, TaskType

logger = logging.getLogger(__name__)


class GeminiResponse(BaseModel):
    """Standardized response from Gemini API."""

    text: str = Field(..., description="Generated text response")
    tokens: int = Field(..., description="Number of tokens used")
    model: str = Field(..., description="Model used for generation")
    finish_reason: str = Field(..., description="Reason for completion")


class GeminiAdapter(LLMAdapter):
    """Adapter for Google Gemini 1.5 Pro model."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-1.5-pro"):
        """Initialize Gemini adapter.

        Args:
            api_key: Google AI API key. If None, will try to get from GOOGLE_AI_API_KEY env var.
            model: Model name to use (default: gemini-1.5-pro)
        """
        self._api_key = api_key or os.getenv("GOOGLE_AI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "Google AI API key not provided. Set GOOGLE_AI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self._model = model
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"
        self._client = httpx.AsyncClient(
            timeout=60.0,
        )

        logger.info(f"Initialized Gemini adapter for model: {self._model}")

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return f"gemini-{self._model}"

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
        """Generate response from prompt using Gemini API.

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
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": context.get("max_tokens", 4000),
                    "temperature": context.get("temperature", 0.7),
                    "topP": context.get("top_p", 0.95),
                    "topK": context.get("top_k", 40),
                },
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                    },
                ],
            }

            logger.debug(f"Sending request to Gemini API: {self._model}")

            # Make the API call
            response = await self._client.post(
                f"{self._base_url}/models/{self._model}:generateContent?key={self._api_key}",
                json=payload,
            )

            if response.status_code != 200:
                error_msg = f"Gemini API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Parse the response
            data = response.json()
            candidates = data.get("candidates", [])

            if not candidates:
                raise RuntimeError("No response candidates from Gemini API")

            candidate = candidates[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])

            if not parts:
                raise RuntimeError("No content parts in Gemini response")

            text = parts[0].get("text", "")

            # Extract token usage (Gemini doesn't always provide this)
            usage_metadata = candidate.get("usageMetadata", {})
            prompt_token_count = usage_metadata.get("promptTokenCount", 0)
            candidates_token_count = usage_metadata.get("candidatesTokenCount", 0)
            total_tokens = prompt_token_count + candidates_token_count

            # If no token count available, estimate based on text length
            if total_tokens == 0:
                total_tokens = len(text.split()) * 1.3  # Rough estimation

            finish_reason = candidate.get("finishReason", "unknown")

            result = {
                "text": text,
                "tokens": int(total_tokens),
                "model": self._model,
                "finish_reason": finish_reason,
            }

            logger.info(f"Generated response with {total_tokens:.0f} tokens")
            return result

        except httpx.RequestError as e:
            error_msg = f"Network error calling Gemini API: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except KeyError as e:
            error_msg = f"Unexpected response format from Gemini API: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except (ValueError, TypeError) as e:
            error_msg = f"Unexpected error in Gemini adapter: {str(e)}"
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
            logger.info("Gemini adapter HTTP client closed")

    def __del__(self) -> None:
        """Cleanup when adapter is destroyed."""
        try:
            # Schedule cleanup in the event loop if it exists
            loop = asyncio.get_running_loop()
            loop.create_task(self.close())
        except RuntimeError:
            # No event loop running, nothing to clean up
            pass


def create_gemini_adapter(
    api_key: str | None = None, model: str = "gemini-1.5-pro"
) -> GeminiAdapter:
    """Factory function to create Gemini adapter.

    Args:
        api_key: Google AI API key. If None, will try to get from GOOGLE_AI_API_KEY env var.
        model: Model name to use (default: gemini-1.5-pro)

    Returns:
        Configured Gemini adapter

    Raises:
        ValueError: If API key is not available
    """
    return GeminiAdapter(api_key=api_key, model=model)
