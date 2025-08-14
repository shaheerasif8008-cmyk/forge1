from __future__ import annotations

from typing import Any


def to_text(value: Any) -> str:
    """Best-effort conversion of arbitrary value to text.

    Ensures a sensible string is returned for assertion checks.
    """
    if value is None:
        return ""
    if isinstance(value, (str | bytes)):
        return value.decode() if isinstance(value, bytes) else value
    # Avoid broad exception catches; str(value) should rarely fail
    text = str(value)
    return text
