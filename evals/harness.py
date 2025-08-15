from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class EvalCase:
    name: str
    task: str
    rubric: dict[str, Any]  # simple rubric: {"must_include": [..], "must_not": [..]}


async def run_case(client: httpx.AsyncClient, base_url: str, token: str | None, case: EvalCase) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    # Execute task through router (no explicit model_name)
    r = await client.post(f"{base_url}/api/v1/ai/execute", json={"task": case.task, "context": {}}, headers=headers)
    out = r.json()
    text = out.get("output", "")
    score = score_text(text, case.rubric)
    return {"name": case.name, "score": score, "output": text, "model": out.get("model_used"), "metadata": out.get("metadata", {})}


def score_text(text: str, rubric: dict[str, Any]) -> float:
    if not text:
        return 0.0
    must = rubric.get("must_include", [])
    must_not = rubric.get("must_not", [])
    s = 1.0
    for m in must:
        if m.lower() not in text.lower():
            s -= 0.2
    for n in must_not:
        if n.lower() in text.lower():
            s -= 0.2
    return max(0.0, min(1.0, s))


async def run_suite(cases: list[EvalCase]) -> dict[str, Any]:
    base_url = os.getenv("FORGE1_API_URL", "http://localhost:8000")
    token = os.getenv("FORGE1_TOKEN")
    async with httpx.AsyncClient(timeout=30.0) as client:
        results = [await run_case(client, base_url, token, c) for c in cases]
    avg = sum(r["score"] for r in results) / max(1, len(results))
    return {"results": results, "average": avg}


