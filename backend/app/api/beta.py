from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps.tenant import beta_gate

router = APIRouter(prefix="/beta", tags=["beta"])


@router.get("/templates")
def list_beta_templates(dep: None = Depends(beta_gate("beta_templates"))) -> dict[str, list[str]]:
    # Return a small set of experimental role templates; static for now
    return {
        "templates": [
            "research_assistant_v2",
            "sales_agent_plus",
            "coder_helper_beta",
        ]
    }


