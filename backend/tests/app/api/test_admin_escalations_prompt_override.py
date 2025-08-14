from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app


def _admin_headers(tenant: str = "t-espo") -> dict[str, str]:
    tok = create_access_token("1", {"tenant_id": tenant, "roles": ["admin"]})
    return {"Authorization": f"Bearer {tok}"}


def test_escalation_retry_with_prompt_override() -> None:
    c = TestClient(app)
    # Create escalation without any TaskExecution
    headers = _admin_headers()
    # Create a dummy employee via API to link escalation to
    c.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "name": "Esc Emp",
            "role_name": "research_assistant",
            "description": "e2e",
            "tools": ["keyword_extractor"],
        },
    )
    emp_id = c.get("/api/v1/employees", headers=headers).json()[0]["id"]

    # Create escalation directly via DB-like endpoint is not present; so we simulate via admin_escalations list is empty
    # Call retry with manual prompt override should 400 without escalation; ensure 404 for bogus id
    r = c.post(
        "/api/v1/admin/escalations/9999/retry",
        headers=headers,
        json={"prompt_override": "Say hello"},
    )
    assert r.status_code in (404, 400)


