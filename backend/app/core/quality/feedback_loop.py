"""Feedback loop utilities for task quality control.

Provides simple heuristics, with an optional LLM-based grader in the future.
"""

from __future__ import annotations

from typing import Any


def score_task(result: Any) -> float:
    """Compute a quality score in [0, 1] for a task result.

    Heuristics used:
    - If result has `success=False` or non-empty `error`, score is low (<= 0.3)
    - Longer outputs and presence of tokens_used increase score modestly
    - If metadata has rag_used and retrieved_docs_count>0, add a small boost

    This function is intentionally lightweight and deterministic. In the future
    an LLM grader can be added behind a feature flag.
    """
    try:
        # Normalize
        success = bool(getattr(result, "success", False)) if hasattr(result, "success") else bool(
            result.get("success", False) if isinstance(result, dict) else False
        )
        error = getattr(result, "error", None) if hasattr(result, "error") else (
            result.get("error") if isinstance(result, dict) else None
        )
        output = getattr(result, "output", "") if hasattr(result, "output") else (
            str(result.get("output", "")) if isinstance(result, dict) else ""
        )
        metadata = getattr(result, "metadata", {}) if hasattr(result, "metadata") else (
            dict(result.get("metadata", {})) if isinstance(result, dict) else {}
        )
        tokens_used = int(metadata.get("tokens_used", 0))

        if not success or (error and str(error).strip()):
            base = 0.2
        else:
            base = 0.6

        # Heuristic signals
        length = len(output.strip())
        if length > 200:
            base += 0.15
        elif length > 50:
            base += 0.08

        if tokens_used > 0:
            base += 0.05

        if metadata.get("rag_used") and int(metadata.get("retrieved_docs_count", 0)) > 0:
            base += 0.05

        # Clamp to [0, 1]
        if base < 0.0:
            base = 0.0
        if base > 1.0:
            base = 1.0
        return float(base)
    except Exception:
        return 0.0


def should_retry(score: float, error: str | None) -> bool:
    """Decide whether to retry based on score and error presence."""
    if error and str(error).strip():
        return True
    return score < 0.55


def next_fix_plan(score: float, error: str | None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Suggest next-step plan to improve outcome.

    Returns a dict that callers can merge into context for a follow-up attempt.
    """
    ctx = dict(context or {})
    plan: dict[str, Any] = {"actions": [], "params": {}}

    if error and str(error).strip():
        plan["actions"].append("address_error")
        plan["params"]["note"] = str(error)[:200]

    # Conservative adjustments first
    plan["params"]["temperature"] = min(0.7, float(ctx.get("temperature", 0.7)))
    plan["params"]["max_tokens"] = max(256, int(ctx.get("max_tokens", 1024)))

    if score < 0.3:
        plan["actions"].extend(["increase_rag", "add_examples", "reduce_scope"])
        plan["params"]["rag_top_k"] = max(5, int(ctx.get("rag_top_k", 5)))
    elif score < 0.55:
        plan["actions"].append("minor_prompt_tweak")
        plan["params"]["hint"] = "Clarify instructions and desired format"
    else:
        plan["actions"].append("accept")

    return plan


