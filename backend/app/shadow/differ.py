from __future__ import annotations

from typing import Optional

from ..core.memory.long_term import _get_embedding as _emb


def semantic_diff_score(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    va = _emb(a)
    vb = _emb(b)
    sim = sum(x * y for x, y in zip(va, vb))
    # map [-1,1] to [0,1]
    return max(0.0, min(1.0, (sim + 1.0) / 2.0))


