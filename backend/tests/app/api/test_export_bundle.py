from __future__ import annotations

import tarfile
import io

from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app


def _headers_admin(tenant: str = "t-export") -> dict[str, str]:
    tok = create_access_token("1", {"tenant_id": tenant, "roles": ["admin"]})
    return {"Authorization": f"Bearer {tok}"}


def test_export_bundle_signature_present() -> None:
    c = TestClient(app)
    c.post(
        "/api/v1/employees/",
        headers=_headers_admin(),
        json={"name": "Exporter", "role_name": "Sales Agent", "description": "d", "tools": ["api_caller"]},
    )
    lst = c.get("/api/v1/employees/", headers=_headers_admin())
    eid = lst.json()[0]["id"]

    resp = c.post(f"/api/v1/admin/employees/{eid}/export", headers=_headers_admin())
    assert resp.status_code == 200
    data = resp.content

    buf = io.BytesIO(data)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        names = set(m.name for m in tar.getmembers())
        assert {"config.yaml", "runner.py", "README.md", "signature.txt", "manifest.json"}.issubset(names)


