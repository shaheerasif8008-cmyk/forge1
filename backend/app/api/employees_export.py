from __future__ import annotations

import io
import json
import tarfile
import hmac
import hashlib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..core.config import settings
from ..db.models import Employee
from ..db.session import get_session


router = APIRouter(prefix="/admin/employees", tags=["admin-export"])


def _sign_manifest(manifest: dict[str, Any]) -> str:
    key = (settings.export_signing_secret or "dev-export-secret").encode()
    body = json.dumps(manifest, sort_keys=True).encode()
    return hmac.new(key, body, hashlib.sha256).hexdigest()


@router.post("/{employee_id}/export")
def export_employee_bundle(
    employee_id: str,
    db: Session = Depends(get_session),  # noqa: B008
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> StreamingResponse:
    emp = db.get(Employee, employee_id)
    if emp is None or emp.tenant_id != current_user.get("tenant_id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    cfg = emp.config or {}
    manifest = {
        "employee_id": emp.id,
        "tenant_id": emp.tenant_id,
        "name": emp.name,
        "config": cfg,
        "version": 1,
    }
    signature = _sign_manifest(manifest)

    # Prepare in-memory tar.gz bundle
    mem = io.BytesIO()
    with tarfile.open(fileobj=mem, mode="w:gz") as tar:
        # config.yaml
        import yaml  # type: ignore

        config_yaml = yaml.safe_dump(cfg, sort_keys=True).encode()
        info = tarfile.TarInfo(name="config.yaml")
        info.size = len(config_yaml)
        tar.addfile(info, io.BytesIO(config_yaml))

        # runner.py
        runner_code = (
            """
#!/usr/bin/env python3
import os, sys, json
import httpx

def main():
    api = os.environ.get("OPENROUTER_API_URL", "https://openrouter.ai/api/v1")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is required")
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Hello"
    r = httpx.post(f"{api}/chat/completions", json={"model":"openai/gpt-4o-mini", "messages":[{"role":"user","content":prompt}]}, headers={"Authorization": f"Bearer {key}"})
    r.raise_for_status()
    print(r.json())

if __name__ == "__main__":
    main()
"""
        ).encode()
        info = tarfile.TarInfo(name="runner.py")
        info.mode = 0o755
        info.size = len(runner_code)
        tar.addfile(info, io.BytesIO(runner_code))

        # README.md
        readme = (
            "# Exported Employee Bundle\n\n"
            "Contents:\n\n"
            "- config.yaml: Employee configuration for routing/tools/RAG\n"
            "- runner.py: Minimal CLI that calls OpenRouter with your prompt\n"
            "\nEnvironment:\n\n"
            "- OPENROUTER_API_KEY: Your API key\n"
            "- OPENROUTER_API_URL: Optional custom base URL\n"
        ).encode()
        info = tarfile.TarInfo(name="README.md")
        info.size = len(readme)
        tar.addfile(info, io.BytesIO(readme))

        # signature.txt (HMAC over manifest)
        sig = signature.encode()
        info = tarfile.TarInfo(name="signature.txt")
        info.size = len(sig)
        tar.addfile(info, io.BytesIO(sig))

        # manifest.json
        man_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode()
        info = tarfile.TarInfo(name="manifest.json")
        info.size = len(man_bytes)
        tar.addfile(info, io.BytesIO(man_bytes))

    mem.seek(0)
    return StreamingResponse(mem, media_type="application/gzip", headers={"Content-Disposition": f"attachment; filename=employee_{employee_id}.tar.gz"})


