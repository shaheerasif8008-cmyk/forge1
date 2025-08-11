"""Memory encoder utilities for summarization and embeddings.

This module provides a `MemoryEncoder` class that can:
- summarize(content): produce a concise summary using OpenAI chat models (default: gpt-5)
- embed(content): generate vector embeddings compatible with pgvector (default: text-embedding-3-small)

It uses direct HTTP calls via httpx to avoid a hard dependency on the OpenAI SDK.
The API key is taken from the OPENAI_API_KEY environment variable by default.
"""

from __future__ import annotations

from typing import Any

import httpx


class MemoryEncoder:
    """Encoder for summarization and embeddings using OpenAI APIs.

    Args:
        api_key: OpenAI API key. If None, uses the OPENAI_API_KEY environment variable.
        base_url: Base URL for the OpenAI API.
        chat_model: Chat model to use for summarization (default: "gpt-5").
        embedding_model: Embedding model to use (default: "text-embedding-3-small" → 1536 dims).
        timeout_seconds: Request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.openai.com/v1",
        chat_model: str = "gpt-5",
        embedding_model: str = "text-embedding-3-small",
        timeout_seconds: float = 60.0,
    ) -> None:
        import os

        self._api_key: str | None = api_key or os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY or pass api_key to MemoryEncoder."
            )

        self._base_url = base_url.rstrip("/")
        self._chat_model = chat_model
        self._embedding_model = embedding_model
        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout_seconds,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        try:
            self._client.close()
        except Exception:  # noqa: BLE001
            # Best-effort close
            pass

    # Context manager support
    def __enter__(self) -> MemoryEncoder:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:  # noqa: ANN401
        self.close()

    def summarize(self, content: str, *, max_tokens: int = 300) -> str:
        """Create a concise summary of the given content using a chat completion.

        Args:
            content: The text to summarize.
            max_tokens: Maximum tokens for the model's response.

        Returns:
            The summarized text.
        """
        if not content.strip():
            return ""

        payload = {
            "model": self._chat_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a highly concise summarizer. Write a clear, neutral summary "
                        "that captures the key points in a few sentences."
                    ),
                },
                {"role": "user", "content": content},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "stream": False,
        }

        try:
            resp = self._client.post(f"{self._base_url}/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            message = choice["message"]
            summary = str(message.get("content", "")).strip()
            return summary
        except httpx.HTTPError as e:  # Network/HTTP errors
            raise RuntimeError(f"OpenAI summarize request failed: {e}") from e
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected summarize response format: {e}") from e

    def embed(self, content: str) -> list[float]:
        """Generate a vector embedding for the given content.

        Uses the embeddings endpoint and returns a list of floats
        suitable for storage in a pgvector column.
        """
        if not content.strip():
            return []

        payload = {
            "model": self._embedding_model,
            "input": content,
        }

        try:
            resp = self._client.post(f"{self._base_url}/embeddings", json=payload)
            resp.raise_for_status()
            data = resp.json()
            embedding = data["data"][0]["embedding"]
            # Ensure the output is a list[float]
            return [float(x) for x in embedding]
        except httpx.HTTPError as e:
            raise RuntimeError(f"OpenAI embedding request failed: {e}") from e
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise RuntimeError(f"Unexpected embedding response format: {e}") from e
